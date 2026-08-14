from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)
from app.services.chat_feedback_service import (
    get_conversation_feedback,
    save_chat_feedback,
)


router = APIRouter(
    prefix="/chat-feedback",
    tags=["Chat Feedback"],
)


class ChatFeedbackRequest(
    BaseModel
):
    conversationId: str = Field(
        min_length=1,
        max_length=64,
    )

    messageId: int = Field(
        gt=0,
    )

    rating: str = Field(
        min_length=2,
        max_length=10,
    )

    comment: str | None = Field(
        default=None,
        max_length=1000,
    )


@router.post("/")
def submit_chat_feedback(
    payload: ChatFeedbackRequest,
    db: Session = Depends(get_db),
):
    try:
        result = save_chat_feedback(
            db,
            conversation_id=(
                payload
                .conversationId
            ),
            message_id=(
                payload
                .messageId
            ),
            rating=(
                payload.rating
            ),
            comment=(
                payload.comment
            ),
        )

        db.commit()

        return result

    except LookupError as exc:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save "
                "chat feedback."
            ),
        ) from exc


@router.get(
    "/conversation/{conversation_id}"
)
def list_conversation_feedback(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    try:
        return (
            get_conversation_feedback(
                db,
                conversation_id=(
                    conversation_id
                ),
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load "
                "chat feedback."
            ),
        ) from exc
