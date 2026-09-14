from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DuplicateFindingRecord(Base):
    __tablename__ = "duplicate_findings"
    __table_args__ = (
        UniqueConstraint(
            "integration_id",
            "primary_source_account_id",
            "duplicate_source_account_id",
            name="uq_duplicate_findings_pair",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    primary_source_account_id: Mapped[int] = mapped_column(
        ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duplicate_source_account_id: Mapped[int] = mapped_column(
        ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    last_scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True
    )

    integration = relationship("IntegrationRecord")
    primary_account = relationship("SourceAccountRecord", foreign_keys=[primary_source_account_id])
    duplicate_account = relationship("SourceAccountRecord", foreign_keys=[duplicate_source_account_id])
