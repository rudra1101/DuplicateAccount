from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base


if TYPE_CHECKING:
    from app.db_models.integration import (
        IntegrationRecord,
    )
    from app.db_models.scan import (
        ScanRecord,
    )


class JobExecutionRecord(Base):
    __tablename__ = "job_executions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    integration_id: Mapped[int] = mapped_column(
        ForeignKey(
            "integrations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    scan_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "scans.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="RUNNING",
        index=True,
    )

    source_file_name: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
    )

    source_path: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    file_checksum: Mapped[
        str | None
    ] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    accounts_scanned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    duplicate_groups: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    duplicate_accounts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        index=True,
    )

    completed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    integration: Mapped[
        "IntegrationRecord"
    ] = relationship(
        "IntegrationRecord",
        back_populates="job_executions",
        foreign_keys=[integration_id],
    )

    scan: Mapped[
        "ScanRecord | None"
    ] = relationship(
        "ScanRecord",
        foreign_keys=[scan_id],
    )