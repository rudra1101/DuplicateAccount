from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReviewCandidateRecord(Base):
    __tablename__ = "review_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    account_1_key: Mapped[str] = mapped_column(String(500), nullable=False)
    account_2_key: Mapped[str] = mapped_column(String(500), nullable=False)
    account_1_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    account_2_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    matched_attributes: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    conflicting_attributes: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reasons: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)

    review_decision: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
