from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db_models.chat_conversation import ChatConversationRecord
from app.db_models.chat_message import ChatMessageRecord


def get_owned_conversation(
    db: Session,
    *,
    conversation_id: str,
    user_id: int,
) -> ChatConversationRecord | None:
    return db.scalar(
        select(ChatConversationRecord).where(
            ChatConversationRecord.id == conversation_id,
            ChatConversationRecord.user_id == user_id,
        )
    )


def ensure_owned_conversation(
    db: Session,
    *,
    conversation_id: str,
    user_id: int,
) -> ChatConversationRecord:
    conversation = get_owned_conversation(
        db,
        conversation_id=conversation_id,
        user_id=user_id,
    )
    if conversation is None:
        raise LookupError("Conversation not found.")
    return conversation


def list_owned_conversations(
    db: Session,
    *,
    user_id: int,
    limit: int = 50,
) -> list[ChatConversationRecord]:
    safe_limit = max(1, min(int(limit), 100))
    return list(
        db.scalars(
            select(ChatConversationRecord)
            .where(ChatConversationRecord.user_id == user_id)
            .order_by(
                ChatConversationRecord.updated_at.desc(),
                ChatConversationRecord.created_at.desc(),
            )
            .limit(safe_limit)
        ).all()
    )


def assign_new_conversation_owner(
    db: Session,
    *,
    conversation: ChatConversationRecord,
    user_id: int,
) -> None:
    if conversation.user_id is None:
        conversation.user_id = user_id
        db.flush()
        return

    if conversation.user_id != user_id:
        raise LookupError("Conversation not found.")


def clear_owned_conversations(
    db: Session,
    *,
    user_id: int,
) -> int:
    conversation_ids = list(
        db.scalars(
            select(ChatConversationRecord.id).where(
                ChatConversationRecord.user_id == user_id
            )
        ).all()
    )

    if not conversation_ids:
        return 0

    db.execute(
        delete(ChatMessageRecord).where(
            ChatMessageRecord.conversation_id.in_(conversation_ids)
        )
    )
    result = db.execute(
        delete(ChatConversationRecord).where(
            ChatConversationRecord.id.in_(conversation_ids),
            ChatConversationRecord.user_id == user_id,
        )
    )
    return int(result.rowcount or 0)
