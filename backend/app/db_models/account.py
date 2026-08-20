from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AccountRecord(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    scan_id: Mapped[int] = mapped_column(
        ForeignKey(
            "scans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    application_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "applications.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    schema_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "application_schemas.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    source_account_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Legacy searchable columns are intentionally retained while the
    # duplicate engine transitions to application-specific schemas.
    application: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    employee_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )

    manager: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    created: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Complete source record. This lets AD, HR, SAP, JDBC, REST, etc.
    # retain different attribute sets without adding DB columns.
    raw_attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    scan = relationship(
        "ScanRecord",
        back_populates="accounts",
    )

    application_record = relationship(
        "ApplicationRecord",
        back_populates="accounts",
        foreign_keys=[application_id],
    )

    schema_record = relationship(
        "ApplicationSchemaRecord",
        back_populates="accounts",
        foreign_keys=[schema_id],
    )