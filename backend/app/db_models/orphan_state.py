from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OrphanStateRecord(Base):
    __tablename__ = "orphan_states"
    __table_args__ = (UniqueConstraint("source_account_id", name="uq_orphan_states_source_account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_account_id: Mapped[int] = mapped_column(ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    orphan_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    correlation_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matched_identity_id: Mapped[int | None] = mapped_column(ForeignKey("identities.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)
    last_scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
