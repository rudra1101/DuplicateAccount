from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db_models.chat_conversation import (
    ChatConversationRecord,
)
from app.db_models.chat_message import (
    ChatMessageRecord,
)


MAX_TITLE_LENGTH = 60


def _iso(
    value: datetime | None,
) -> str | None:
    return (
        value.isoformat()
        if value is not None
        else None
    )


def generate_conversation_title(
    message: str,
) -> str:
    normalized = " ".join(
        str(message or "")
        .strip()
        .split()
    )

    if not normalized:
        return "New Conversation"

    if (
        len(normalized)
        <= MAX_TITLE_LENGTH
    ):
        return normalized

    return (
        normalized[
            : MAX_TITLE_LENGTH - 1
        ].rstrip()
        + "…"
    )


def serialize_conversation_summary(
    conversation: ChatConversationRecord,
) -> dict:
    return {
        "id": conversation.id,
        "title": (
            conversation.title
            or "New Conversation"
        ),
        "createdAt": _iso(
            conversation.created_at
        ),
        "updatedAt": _iso(
            conversation.updated_at
        ),
    }


def serialize_message(
    message: ChatMessageRecord,
) -> dict:
    return {
        "id": message.id,
        "conversationId":
            message.conversation_id,
        "role": message.role,
        "content": message.content,
        "model": message.model,
        "sources":
            message.sources or [],
        "createdAt": _iso(
            message.created_at
        ),
    }


# ============================================================
# Conversation create/get
# ============================================================

def get_or_create_conversation(
    db: Session,
    *,
    conversation_id: str,
    first_message: str,
) -> ChatConversationRecord:
    conversation = db.get(
        ChatConversationRecord,
        conversation_id,
    )

    if conversation is not None:
        return conversation

    conversation = (
        ChatConversationRecord(
            id=conversation_id,
            title=(
                generate_conversation_title(
                    first_message
                )
            ),
        )
    )

    db.add(conversation)
    db.flush()

    return conversation


# Compatibility name used by some versions of app/api/chat.py.
def get_or_create_chat_conversation(
    db: Session,
    *,
    conversation_id: str,
    first_message: str,
) -> ChatConversationRecord:
    return get_or_create_conversation(
        db,
        conversation_id=(
            conversation_id
        ),
        first_message=first_message,
    )


# ============================================================
# Save chat message
# ============================================================

def save_message(
    db: Session,
    *,
    conversation_id: str,
    role: str,
    content: str,
    model: str | None = None,
    sources: list[dict] | None = None,
) -> ChatMessageRecord:
    message = ChatMessageRecord(
        conversation_id=(
            conversation_id
        ),
        role=role,
        content=content,
        model=model,
        sources=sources or [],
    )

    db.add(message)

    conversation = db.get(
        ChatConversationRecord,
        conversation_id,
    )

    if conversation is not None:
        conversation.updated_at = (
            datetime.utcnow()
        )

    db.flush()

    return message


# IMPORTANT:
# Your app/api/chat.py currently imports save_chat_message.
# Keep this compatibility wrapper.
def save_chat_message(
    db: Session,
    *,
    conversation_id: str,
    role: str,
    content: str,
    model: str | None = None,
    sources: list[dict] | None = None,
) -> ChatMessageRecord:
    return save_message(
        db,
        conversation_id=(
            conversation_id
        ),
        role=role,
        content=content,
        model=model,
        sources=sources,
    )


# ============================================================
# List conversations
# ============================================================

def list_conversations(
    db: Session,
    *,
    limit: int = 50,
) -> list[dict]:
    safe_limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    statement = (
        select(
            ChatConversationRecord
        )
        .order_by(
            ChatConversationRecord
            .updated_at
            .desc(),
            ChatConversationRecord
            .created_at
            .desc(),
        )
        .limit(safe_limit)
    )

    conversations = list(
        db.scalars(
            statement
        ).all()
    )

    return [
        serialize_conversation_summary(
            conversation
        )
        for conversation
        in conversations
    ]


# Compatibility alias.
def list_chat_conversations(
    db: Session,
    *,
    limit: int = 50,
) -> list[dict]:
    return list_conversations(
        db,
        limit=limit,
    )


# ============================================================
# Conversation details
# ============================================================

def get_conversation_details(
    db: Session,
    *,
    conversation_id: str,
) -> dict | None:
    statement = (
        select(
            ChatConversationRecord
        )
        .options(
            selectinload(
                ChatConversationRecord
                .messages
            )
        )
        .where(
            ChatConversationRecord.id
            == conversation_id
        )
    )

    conversation = (
        db.scalars(
            statement
        ).first()
    )

    if conversation is None:
        return None

    messages = sorted(
        list(
            conversation.messages
        ),
        key=lambda item: (
            item.created_at,
            item.id,
        ),
    )

    return {
        **serialize_conversation_summary(
            conversation
        ),
        "messages": [
            serialize_message(
                message
            )
            for message in messages
        ],
    }


# Compatibility alias.
def get_chat_conversation(
    db: Session,
    *,
    conversation_id: str,
) -> dict | None:
    return get_conversation_details(
        db,
        conversation_id=(
            conversation_id
        ),
    )


# ============================================================
# Rename conversation
# ============================================================

def rename_conversation(
    db: Session,
    *,
    conversation_id: str,
    title: str,
) -> dict | None:
    normalized_title = " ".join(
        str(title or "")
        .strip()
        .split()
    )

    if not normalized_title:
        raise ValueError(
            "Conversation title "
            "cannot be empty."
        )

    if (
        len(normalized_title)
        > MAX_TITLE_LENGTH
    ):
        raise ValueError(
            "Conversation title "
            f"cannot exceed "
            f"{MAX_TITLE_LENGTH} "
            "characters."
        )

    conversation = db.get(
        ChatConversationRecord,
        conversation_id,
    )

    if conversation is None:
        return None

    conversation.title = (
        normalized_title
    )

    conversation.updated_at = (
        datetime.utcnow()
    )

    db.flush()

    return (
        serialize_conversation_summary(
            conversation
        )
    )


# Compatibility alias.
def rename_chat_conversation(
    db: Session,
    *,
    conversation_id: str,
    title: str,
) -> dict | None:
    return rename_conversation(
        db,
        conversation_id=(
            conversation_id
        ),
        title=title,
    )


# ============================================================
# Delete one conversation
# ============================================================

def delete_conversation(
    db: Session,
    *,
    conversation_id: str,
) -> bool:
    conversation = db.get(
        ChatConversationRecord,
        conversation_id,
    )

    if conversation is None:
        return False

    db.delete(conversation)
    db.flush()

    return True


# Compatibility alias.
def delete_chat_conversation(
    db: Session,
    *,
    conversation_id: str,
) -> bool:
    return delete_conversation(
        db,
        conversation_id=(
            conversation_id
        ),
    )


# ============================================================
# Clear all conversations
# ============================================================

def clear_conversations(
    db: Session,
) -> int:
    conversation_ids = list(
        db.scalars(
            select(
                ChatConversationRecord.id
            )
        ).all()
    )

    if not conversation_ids:
        return 0

    db.execute(
        delete(
            ChatMessageRecord
        ).where(
            ChatMessageRecord
            .conversation_id
            .in_(
                conversation_ids
            )
        )
    )

    result = db.execute(
        delete(
            ChatConversationRecord
        ).where(
            ChatConversationRecord
            .id
            .in_(
                conversation_ids
            )
        )
    )

    return int(
        result.rowcount or 0
    )


# Compatibility alias.
def clear_chat_conversations(
    db: Session,
) -> int:
    return clear_conversations(
        db
    )