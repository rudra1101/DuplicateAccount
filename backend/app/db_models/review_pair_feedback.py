from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReviewPairFeedbackRecord(Base):
    __tablename__ = "review_pair_feedback"
    __table_args__ = (
        UniqueConstraint(
            "integration_id",
            "application",
            "account_1_key",
            "account_2_key",
            name="uq_review_pair_feedback_pair",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_1_key: Mapped[str] = mapped_column(String(500), nullable=False)
    account_2_key: Mapped[str] = mapped_column(String(500), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_review_candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
