from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DuplicateGroupRecord(Base):
    __tablename__ = "duplicate_groups"

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

    application: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    primary_username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    duplicate_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    highest_confidence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    scan = relationship(
        "ScanRecord",
        back_populates="duplicate_groups",
    )

    candidates = relationship(
        "DuplicateCandidateRecord",
        back_populates="group",
        cascade="all, delete-orphan",
    )