from __future__ import annotations

import json
import re
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
)
from fastapi.responses import (
    StreamingResponse,
)
from sqlalchemy.orm import Session

from app.ai.fast_agent_service import (
    run_identity_agent_stream_fast,
)
from app.ai.authorization import (
    permissions_for_user,
    reset_rudrix_permissions,
    set_rudrix_permissions,
)
from app.auth import get_current_user
from app.database.session import (
    get_db,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ToolInvocationResponse,
)
from app.services.chat_history_service import (
    get_or_create_chat_conversation,
    save_chat_message,
)
from app.services.service_desk_service import create_ticket


router = APIRouter(
    prefix="/chat",
    tags=["AI Assistant"],
    dependencies=[Depends(get_current_user)],
)

_CONFIRMATION_WORDS = {
    "confirm",
    "confirmed",
    "yes",
    "yes confirm",
    "yes, confirm",
    "proceed",
    "go ahead",
    "do it",
}


def _event(event_type: str, **payload: Any) -> str:
    return json.dumps({"type": event_type, **payload}, default=str) + "\n"


def _next_authorized_event(iterator, permissions: frozenset[str]):
    """Advance one streaming step with the user's current Rudrix permissions."""
    token = set_rudrix_permissions(permissions)
    try:
        return next(iterator)
    finally:
        reset_rudrix_permissions(token)


def _ticket_confirmation_arguments(payload: ChatRequest) -> dict[str, Any] | None:
    """Recover a ticket action only from Rudrix's immediately prior confirmation.

    A one-word confirmation is intentionally not sent back through the LLM to
    reinterpret a destructive action. The preceding assistant message must have
    explicitly asked for confirmation and contain the remediation item, target
    account, and requested DISABLE/DELETE action.
    """
    current = " ".join(str(payload.message or "").strip().lower().split())
    if current not in _CONFIRMATION_WORDS:
        return None

    history = list(payload.history or [])
    if not history:
        return None

    previous_assistant = next(
        (
            str(message.content or "")
            for message in reversed(history)
            if str(message.role or "").lower() == "assistant"
        ),
        "",
    )
    if not previous_assistant:
        return None

    assistant_lower = previous_assistant.lower()
    if "confirm" not in assistant_lower or "ticket" not in assistant_lower:
        return None

    item_match = re.search(
        r"remediation\s+item(?:\s+id)?\s*[:#]?\s*(\d+)",
        previous_assistant,
        flags=re.IGNORECASE,
    )
    if not item_match:
        return None

    # Prefer an explicit target in the sentence describing the ticket action.
    target_match = re.search(
        r"(?:delete|deleting|disable|disabling)[^\n.]{0,120}?account\s*([12])\b",
        previous_assistant,
        flags=re.IGNORECASE,
    )
    if not target_match:
        target_match = re.search(
            r"target(?:\s+account)?\s*[:#]?\s*account\s*([12])\b",
            previous_assistant,
            flags=re.IGNORECASE,
        )
    if not target_match:
        return None

    action_match = re.search(
        r"\b(delete|deleting|disable|disabling)\b",
        previous_assistant,
        flags=re.IGNORECASE,
    )
    if not action_match:
        return None

    raw_action = action_match.group(1).lower()
    action = "DELETE" if raw_action.startswith("delet") else "DISABLE"
    target = "ACCOUNT_1" if target_match.group(1) == "1" else "ACCOUNT_2"

    return {
        "remediation_item_id": int(item_match.group(1)),
        "target": target,
        "action": action,
    }


def _ticket_confirmation_response(
    *,
    db: Session,
    payload: ChatRequest,
    conversation_id: str,
    permissions: frozenset[str],
) -> ChatResponse | None:
    arguments = _ticket_confirmation_arguments(payload)
    if arguments is None:
        return None

    if "*" not in permissions and "remediation.manage" not in permissions:
        return ChatResponse(
            conversationId=conversation_id,
            message=(
                "You do not have permission to create remediation tickets. "
                "The required permission is `remediation.manage`."
            ),
            model="rudrix-action",
        )

    result = create_ticket(
        db,
        item_id=int(arguments["remediation_item_id"]),
        target=str(arguments["target"]),
        action=str(arguments["action"]),
        requested_by="Rudrix",
    )

    ticket_id = result.get("ticketId") or "created ticket"
    target_key = result.get("targetAccountKey") or arguments["target"]
    ticket_url = result.get("ticketUrl")
    message = (
        f"Created Service Desk ticket **{ticket_id}** to "
        f"**{str(arguments['action']).lower()}** account `{target_key}`."
    )
    if ticket_url:
        message += f" [Open ticket]({ticket_url})"

    return ChatResponse(
        conversationId=conversation_id,
        message=message,
        model="rudrix-action",
        toolsUsed=[
            ToolInvocationResponse(
                name="create_remediation_ticket",
                arguments=arguments,
                result={"success": True, "data": result},
            )
        ],
    )


@router.post("/stream")
def stream_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    conversation_id = payload.conversationId or str(uuid.uuid4())
    request = payload.model_copy(update={"conversationId": conversation_id})

    # Resolve permissions from the same request DB session used by the chat
    # endpoint. This keeps Rudrix permission-driven for ADMIN, USER and custom
    # roles and avoids stale/detached middleware role relationships.
    user_permissions = permissions_for_user(user, db=db)

    def generate():
        committed = False

        try:
            yield _event("start", conversationId=conversation_id)

            final_response = _ticket_confirmation_response(
                db=db,
                payload=payload,
                conversation_id=conversation_id,
                permissions=user_permissions,
            )

            if final_response is not None:
                yield _event("status", message="Creating Service Desk ticket...")
                yield _event("delta", text=final_response.message)
            else:
                agent_events = iter(
                    run_identity_agent_stream_fast(
                        db=db,
                        request=request,
                    )
                )

                while True:
                    try:
                        event = _next_authorized_event(
                            agent_events,
                            user_permissions,
                        )
                    except StopIteration:
                        break

                    event_type = event.get("type")

                    if event_type == "status":
                        yield _event(
                            "status",
                            message=event.get("message", ""),
                        )
                        continue

                    if event_type == "delta":
                        text = str(event.get("text") or "")
                        if text:
                            yield _event("delta", text=text)
                        continue

                    if event_type == "done":
                        final_response = event.get("response")

            if final_response is None:
                raise RuntimeError(
                    "Rudrix streaming finished without a final response."
                )

            get_or_create_chat_conversation(
                db,
                conversation_id=conversation_id,
                first_message=payload.message,
            )
            save_chat_message(
                db,
                conversation_id=conversation_id,
                role="user",
                content=payload.message,
            )
            assistant_record = save_chat_message(
                db,
                conversation_id=conversation_id,
                role="assistant",
                content=final_response.message,
                model=final_response.model,
                sources=[source.model_dump() for source in final_response.sources],
            )

            db.commit()
            committed = True

            yield _event(
                "done",
                conversationId=conversation_id,
                messageId=assistant_record.id,
                model=final_response.model,
                sources=[source.model_dump() for source in final_response.sources],
                toolsUsed=[tool.model_dump() for tool in final_response.toolsUsed],
            )

        except GeneratorExit:
            if not committed:
                db.rollback()
            raise
        except Exception:
            if not committed:
                db.rollback()
            yield _event(
                "error",
                message="AI assistant streaming request failed.",
            )

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
