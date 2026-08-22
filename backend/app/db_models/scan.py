from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


if TYPE_CHECKING:
    from app.db_models.account import AccountRecord
    from app.db_models.duplicate_group import DuplicateGroupRecord
    from app.db_models.integration import IntegrationRecord


class ScanRecord(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED", index=True)
    accounts_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    application_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_group_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_account_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_confidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    integration: Mapped["IntegrationRecord | None"] = relationship(
        "IntegrationRecord",
        back_populates="scans",
        foreign_keys=[integration_id],
    )
    accounts: Mapped[list["AccountRecord"]] = relationship(
        "AccountRecord",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
    duplicate_groups: Mapped[list["DuplicateGroupRecord"]] = relationship(
        "DuplicateGroupRecord",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
