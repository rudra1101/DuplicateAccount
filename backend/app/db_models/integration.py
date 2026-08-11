from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
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
    from app.db_models.job_execution import (
        JobExecutionRecord,
    )
    from app.db_models.job_schedule import (
        JobScheduleRecord,
    )
    from app.db_models.scan import (
        ScanRecord,
    )


class IntegrationRecord(Base):
    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    connector_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    description: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    configuration: Mapped[
        dict[str, Any]
    ] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
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

    # ---------------------------------------------
    # Latest and historical scans for integration
    # ---------------------------------------------

    scans: Mapped[
        list["ScanRecord"]
    ] = relationship(
        "ScanRecord",
        back_populates="integration",
        passive_deletes=True,
    )

    # ---------------------------------------------
    # Integration execution history
    # ---------------------------------------------

    job_executions: Mapped[
        list["JobExecutionRecord"]
    ] = relationship(
        "JobExecutionRecord",
        back_populates="integration",
        passive_deletes=True,
    )

    # ---------------------------------------------
    # One scheduler configuration per integration
    # ---------------------------------------------

    schedule: Mapped[
        "JobScheduleRecord | None"
    ] = relationship(
        "JobScheduleRecord",
        back_populates="integration",
        uselist=False,
        cascade=(
            "all, delete-orphan"
        ),
        passive_deletes=True,
        single_parent=True,
    )