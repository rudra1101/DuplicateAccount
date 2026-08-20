from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Float,
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
    from app.db_models.application_schema import ApplicationSchemaRecord


class SchemaAttributeRecord(Base):
    __tablename__ = "schema_attributes"
    __table_args__ = (
        UniqueConstraint(
            "schema_id",
            "name",
            name="uq_schema_attributes_schema_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    schema_id: Mapped[int] = mapped_column(
        ForeignKey(
            "application_schemas.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="string",
    )

    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    multi_valued: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    use_for_matching: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    match_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    match_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    normalization_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    schema: Mapped["ApplicationSchemaRecord"] = relationship(
        "ApplicationSchemaRecord",
        back_populates="attributes",
    )
