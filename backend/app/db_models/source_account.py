from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SourceAccountRecord(Base):
    __tablename__ = "source_accounts"
    __table_args__ = (
        UniqueConstraint(
            "integration_id",
            "application",
            "native_identity",
            name="uq_source_accounts_integration_application_native",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    schema_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_schemas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    application: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    native_identity: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    employee_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    raw_attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    attribute_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    last_scan_id: Mapped[int | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    integration = relationship("IntegrationRecord")
    application_record = relationship("ApplicationRecord", foreign_keys=[application_id])
    schema_record = relationship("ApplicationSchemaRecord", foreign_keys=[schema_id])
