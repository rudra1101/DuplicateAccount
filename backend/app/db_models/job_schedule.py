from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
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


class JobScheduleRecord(Base):
    __tablename__ = "job_schedules"

    __table_args__ = (
        UniqueConstraint(
            "integration_id",
            name=(
                "uq_job_schedules_"
                "integration_id"
            ),
        ),
    )

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    schedule_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CRON",
    )

    cron_expression: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Asia/Kolkata",
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    last_run_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_run_status: Mapped[
        str | None
    ] = mapped_column(
        String(50),
        nullable=True,
    )

    next_run_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_error: Mapped[
        str | None
    ] = mapped_column(
        String(2000),
        nullable=True,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    integration: Mapped[
        "IntegrationRecord"
    ] = relationship(
        "IntegrationRecord",
        back_populates="schedule",
        foreign_keys=[
            integration_id,
        ],
    )