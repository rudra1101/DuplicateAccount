from __future__ import annotations

import json
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

from app.ai.agent_service import (
    run_identity_agent_stream,
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
)
from app.services.chat_history_service import (
    get_or_create_chat_conversation,
    save_chat_message,
)


router = APIRouter(
    prefix="/chat",
    tags=["AI Assistant"],
    dependencies=[
        Depends(get_current_user),
    ],
)


def _event(
    event_type: str,
    **payload: Any,
) -> str:
    return (
        json.dumps(
            {
                "type":
                    event_type,
                **payload,
            },
            default=str,
        )
        + "\n"
    )


@router.post("/stream")
def stream_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    conversation_id = (
        payload.conversationId
        or str(
            uuid.uuid4()
        )
    )

    request = payload.model_copy(
        update={
            "conversationId":
                conversation_id,
        }
    )

    user_permissions = permissions_for_user(user)

    def generate():
        committed = False
        permission_token = set_rudrix_permissions(
            user_permissions
        )

        try:
            yield _event(
                "start",
                conversationId=
                    conversation_id,
            )

            final_response = None

            for event in (
                run_identity_agent_stream(
                    db=db,
                    request=request,
                )
            ):
                event_type = (
                    event.get(
                        "type"
                    )
                )

                if event_type == (
                    "status"
                ):
                    yield _event(
                        "status",
                        message=
                            event.get(
                                "message",
                                "",
                            ),
                    )
                    continue

                if event_type == (
                    "delta"
                ):
                    text = str(
                        event.get(
                            "text"
                        )
                        or ""
                    )

                    if text:
                        yield _event(
                            "delta",
                            text=text,
                        )

                    continue

                if event_type == (
                    "done"
                ):
                    final_response = (
                        event.get(
                            "response"
                        )
                    )

            if final_response is None:
                raise RuntimeError(
                    "Rudrix streaming finished "
                    "without a final response."
                )

            get_or_create_chat_conversation(
                db,
                conversation_id=
                    conversation_id,
                first_message=
                    payload.message,
            )

            save_chat_message(
                db,
                conversation_id=
                    conversation_id,
                role="user",
                content=
                    payload.message,
            )

            assistant_record = (
                save_chat_message(
                    db,
                    conversation_id=
                        conversation_id,
                    role="assistant",
                    content=
                        final_response
                        .message,
                    model=
                        final_response
                        .model,
                    sources=[
                        source.model_dump()
                        for source
                        in final_response
                        .sources
                    ],
                )
            )

            db.commit()
            committed = True

            yield _event(
                "done",
                conversationId=
                    conversation_id,
                messageId=
                    assistant_record.id,
                model=
                    final_response
                    .model,
                sources=[
                    source.model_dump()
                    for source
                    in final_response
                    .sources
                ],
                toolsUsed=[
                    tool.model_dump()
                    for tool
                    in final_response
                    .toolsUsed
                ],
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
                message=(
                    "AI assistant streaming request failed."
                ),
            )

        finally:
            reset_rudrix_permissions(
                permission_token
            )

    return StreamingResponse(
        generate(),
        media_type=(
            "application/x-ndjson"
        ),
        headers={
            "Cache-Control":
                "no-cache",
            "X-Accel-Buffering":
                "no",
        },
    )
