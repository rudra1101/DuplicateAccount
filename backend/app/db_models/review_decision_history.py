from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReviewDecisionHistoryRecord(Base):
    __tablename__ = "review_decision_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_1_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    account_2_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="REVIEW")
    account_1_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    account_2_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
