from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.chat_feedback import (
    ChatFeedbackRecord,
)
from app.db_models.chat_message import (
    ChatMessageRecord,
)


VALID_RATINGS = {
    "UP",
    "DOWN",
}


def ensure_feedback_table(
    db: Session,
) -> None:
    """
    Create the feedback table on first use.

    This keeps the feature self-contained and avoids requiring
    an Alembic migration just to test it. The table is only
    created when it does not already exist.
    """
    ChatFeedbackRecord.__table__.create(
        bind=db.get_bind(),
        checkfirst=True,
    )


def serialize_feedback(
    feedback: ChatFeedbackRecord,
) -> dict:
    return {
        "id": feedback.id,
        "messageId":
            feedback.message_id,
        "conversationId":
            feedback.conversation_id,
        "rating":
            feedback.rating,
        "comment":
            feedback.comment,
        "createdAt": (
            feedback.created_at.isoformat()
            if feedback.created_at
            else None
        ),
        "updatedAt": (
            feedback.updated_at.isoformat()
            if feedback.updated_at
            else None
        ),
    }


def save_chat_feedback(
    db: Session,
    *,
    conversation_id: str,
    message_id: int,
    rating: str,
    comment: str | None = None,
) -> dict:
    ensure_feedback_table(
        db
    )

    normalized_rating = (
        str(rating or "")
        .strip()
        .upper()
    )

    if (
        normalized_rating
        not in VALID_RATINGS
    ):
        raise ValueError(
            "Rating must be UP or DOWN."
        )

    normalized_comment = (
        str(comment)
        .strip()
        if comment is not None
        and str(comment).strip()
        else None
    )

    if (
        normalized_comment is not None
        and len(
            normalized_comment
        ) > 1000
    ):
        raise ValueError(
            "Feedback comment cannot "
            "exceed 1000 characters."
        )

    message = db.get(
        ChatMessageRecord,
        message_id,
    )

    if message is None:
        raise LookupError(
            "Chat message was not found."
        )

    if (
        message.conversation_id
        != conversation_id
    ):
        raise ValueError(
            "Message does not belong "
            "to this conversation."
        )

    if (
        message.role
        != "assistant"
    ):
        raise ValueError(
            "Feedback can only be "
            "submitted for assistant "
            "messages."
        )

    statement = (
        select(
            ChatFeedbackRecord
        )
        .where(
            ChatFeedbackRecord
            .message_id
            == message_id
        )
    )

    feedback = (
        db.scalars(
            statement
        ).first()
    )

    now = datetime.utcnow()

    if feedback is None:
        feedback = (
            ChatFeedbackRecord(
                message_id=
                    message_id,
                conversation_id=
                    conversation_id,
                rating=
                    normalized_rating,
                comment=
                    normalized_comment,
                created_at=now,
                updated_at=now,
            )
        )

        db.add(
            feedback
        )
    else:
        feedback.rating = (
            normalized_rating
        )
        feedback.comment = (
            normalized_comment
        )
        feedback.updated_at = (
            now
        )

    db.flush()

    return (
        serialize_feedback(
            feedback
        )
    )


def get_conversation_feedback(
    db: Session,
    *,
    conversation_id: str,
) -> list[dict]:
    ensure_feedback_table(
        db
    )

    statement = (
        select(
            ChatFeedbackRecord
        )
        .where(
            ChatFeedbackRecord
            .conversation_id
            == conversation_id
        )
        .order_by(
            ChatFeedbackRecord
            .message_id
            .asc()
        )
    )

    feedback_rows = list(
        db.scalars(
            statement
        ).all()
    )

    return [
        serialize_feedback(
            feedback
        )
        for feedback
        in feedback_rows
    ]


def delete_message_feedback(
    db: Session,
    *,
    message_id: int,
) -> bool:
    """
    Useful for regeneration: feedback belongs to the exact
    assistant response. When that response is replaced, its
    feedback should not carry over to the new answer.
    """
    ensure_feedback_table(
        db
    )

    statement = (
        select(
            ChatFeedbackRecord
        )
        .where(
            ChatFeedbackRecord
            .message_id
            == message_id
        )
    )

    feedback = (
        db.scalars(
            statement
        ).first()
    )

    if feedback is None:
        return False

    db.delete(
        feedback
    )

    db.flush()

    return True