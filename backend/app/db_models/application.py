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
    from app.db_models.account import AccountRecord
    from app.db_models.application_schema import ApplicationSchemaRecord
    from app.db_models.integration import IntegrationRecord


class ApplicationRecord(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "integration_id",
            "name",
            name="uq_applications_integration_name",
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
        index=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    object_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    integration: Mapped["IntegrationRecord"] = relationship(
        "IntegrationRecord",
        back_populates="applications",
    )

    schemas: Mapped[list["ApplicationSchemaRecord"]] = relationship(
        "ApplicationSchemaRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    accounts: Mapped[list["AccountRecord"]] = relationship(
        "AccountRecord",
        back_populates="application_record",
    )
