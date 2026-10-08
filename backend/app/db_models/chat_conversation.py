from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


if TYPE_CHECKING:
    from app.db_models.chat_message import (
        ChatMessageRecord,
    )


class ChatConversationRecord(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    # Nullable only for legacy conversations created before chat ownership
    # existed. API endpoints never expose unowned conversations.
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Conversation",
    )

    # Grounded Rudrix Agent Core state. This stores only structured entities and
    # action context derived from successful IdentityAI tool results; model prose
    # is never persisted as authoritative agent state.
    agent_state: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    messages: Mapped[
        list["ChatMessageRecord"]
    ] = relationship(
        "ChatMessageRecord",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessageRecord.created_at",
    )
