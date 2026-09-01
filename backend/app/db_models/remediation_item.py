from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RemediationItemRecord(Base):
    __tablename__ = "remediation_items"
    __table_args__ = (
        UniqueConstraint(
            "integration_id",
            "application",
            "account_1_key",
            "account_2_key",
            name="uq_remediation_item_pair",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_1_key: Mapped[str] = mapped_column(String(500), nullable=False)
    account_2_key: Mapped[str] = mapped_column(String(500), nullable=False)
    account_1_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    account_2_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_ACTION", index=True)
    action_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    actioned_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    remediation_action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_account_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service_desk_ticket_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_desk_ticket_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_desk_ticket_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    ticket_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
