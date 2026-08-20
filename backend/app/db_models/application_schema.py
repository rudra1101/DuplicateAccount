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
    from app.db_models.application import ApplicationRecord
    from app.db_models.schema_attribute import SchemaAttributeRecord


class ApplicationSchemaRecord(Base):
    __tablename__ = "application_schemas"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "version",
            name="uq_application_schemas_application_version",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey(
            "applications.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
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

    application: Mapped["ApplicationRecord"] = relationship(
        "ApplicationRecord",
        back_populates="schemas",
    )

    attributes: Mapped[list["SchemaAttributeRecord"]] = relationship(
        "SchemaAttributeRecord",
        back_populates="schema",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SchemaAttributeRecord.position",
    )

    accounts: Mapped[list["AccountRecord"]] = relationship(
        "AccountRecord",
        back_populates="schema_record",
    )
