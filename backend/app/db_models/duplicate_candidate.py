from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,relationship
)

from datetime import datetime

from sqlalchemy import DateTime, Text, func
from app.database.base import Base


class DuplicateCandidateRecord(Base):
    __tablename__ = "duplicate_candidates"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "duplicate_groups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    candidate_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    group = relationship(
        "DuplicateGroupRecord",
        back_populates="candidates",
    )

    username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    recommendation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REVIEW",
    )

    matched_attributes: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    different_attributes: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    account_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    classification: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    reasons: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    warnings: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    features: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    training_labels = relationship(
    "DuplicateTrainingLabelRecord",
    back_populates="candidate",
    cascade="all, delete-orphan",
    )

    review_decision: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )

    review_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reviewer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )