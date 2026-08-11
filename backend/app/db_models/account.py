from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
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

    source_account_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

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

    scan = relationship(
        "ScanRecord",
        back_populates="accounts",
    )