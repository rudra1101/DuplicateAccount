from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.authorization import (
    permissions_for_user,
    reset_rudrix_actor,
    reset_rudrix_permissions,
    set_rudrix_actor,
    set_rudrix_permissions,
)
from app.ai.fast_agent_service import run_identity_agent_stream_fast
from app.auth import get_current_user
from app.database.session import get_db
from app.db_models.chat_conversation import ChatConversationRecord
from app.observability import logger
from app.schemas.chat import ChatRequest
from app.services.chat_history_service import (
    get_or_create_chat_conversation,
    save_chat_message,
)
from app.services.chat_ownership_service import assign_new_conversation_owner


router = APIRouter(
    prefix="/chat",
    tags=["AI Assistant"],
    dependencies=[Depends(get_current_user)],
)


def _event(event_type: str, **payload: Any) -> str:
    return json.dumps({"type": event_type, **payload}, default=str) + "\n"


def _safe_stream_error_message(exc: Exception) -> str:
    detail = str(exc or "").strip().lower()

    if "ollama" in detail and any(
        marker in detail
        for marker in ("connect", "connection", "unavailable", "refused")
    ):
        return (
            "Rudrix cannot connect to Ollama. Start Ollama and verify "
            "the configured OLLAMA_BASE_URL."
        )

    if "model" in detail and any(
        marker in detail
        for marker in ("not found", "missing", "pull")
    ):
        return (
            "A required Ollama model is not installed. Pull the configured "
            "chat and embedding models, then try again."
        )

    return "AI assistant streaming request failed."


def _next_authorized_event(iterator, permissions: frozenset[str], actor: str):
    permission_token = set_rudrix_permissions(permissions)
    actor_token = set_rudrix_actor(actor)
    try:
        return next(iterator)
    finally:
        reset_rudrix_actor(actor_token)
        reset_rudrix_permissions(permission_token)


@router.post("/stream")
def stream_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    existing = None
    if payload.conversationId:
        existing = db.get(ChatConversationRecord, payload.conversationId)
        if existing is not None and existing.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    persisted_agent_state = (
        existing.agent_state
        if existing is not None and isinstance(existing.agent_state, dict)
        else None
    )

    conversation_id = payload.conversationId or str(uuid.uuid4())
    request = payload.model_copy(update={"conversationId": conversation_id})

    user_permissions = permissions_for_user(user, db=db)
    actor = (
        str(getattr(user, "full_name", "") or "").strip()
        or str(getattr(user, "username", "") or "").strip()
        or f"user:{getattr(user, 'id', 'unknown')}"
    )

    def generate():
        committed = False
        agent_state = persisted_agent_state

        try:
            yield _event("start", conversationId=conversation_id)

            final_response = None
            agent_events = iter(
                run_identity_agent_stream_fast(
                    db=db,
                    request=request,
                    persisted_state=persisted_agent_state,
                )
            )

            while True:
                try:
                    event = _next_authorized_event(
                        agent_events,
                        user_permissions,
                        actor,
                    )
                except StopIteration:
                    break

                event_type = event.get("type")
                if event_type == "status":
                    yield _event("status", message=event.get("message", ""))
                    continue

                if event_type == "delta":
                    text = str(event.get("text") or "")
                    if text:
                        yield _event("delta", text=text)
                    continue

                if event_type == "done":
                    final_response = event.get("response")
                    returned_state = event.get("agentState")
                    if isinstance(returned_state, dict):
                        agent_state = returned_state

            if final_response is None:
                raise RuntimeError("Rudrix streaming finished without a final response.")

            conversation = get_or_create_chat_conversation(
                db,
                conversation_id=conversation_id,
                first_message=payload.message,
            )
            if conversation is not None:
                assign_new_conversation_owner(
                    db,
                    conversation=conversation,
                    user_id=user.id,
                )
                if isinstance(agent_state, dict):
                    conversation.agent_state = agent_state

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
        except Exception as exc:
            if not committed:
                db.rollback()
            logger.exception(
                "rudrix_stream_failed",
                exc_info=exc,
                extra={
                    "conversation_id": conversation_id,
                    "actor": actor,
                },
            )
            yield _event(
                "error",
                message=_safe_stream_error_message(exc),
            )

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
