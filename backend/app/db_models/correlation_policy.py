from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


if TYPE_CHECKING:
    from app.db_models.integration import IntegrationRecord


class CorrelationPolicyRecord(Base):
    __tablename__ = "correlation_policies"
    __table_args__ = (
        UniqueConstraint(
            "account_integration_id",
            "authoritative_integration_id",
            "name",
            name="uq_correlation_policy_pair_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    authoritative_integration_id: Mapped[int] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy: Mapped[str] = mapped_column(
        String(40), nullable=False, default="FIRST_MATCH_WINS"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    account_integration: Mapped["IntegrationRecord"] = relationship(
        "IntegrationRecord", foreign_keys=[account_integration_id]
    )
    authoritative_integration: Mapped["IntegrationRecord"] = relationship(
        "IntegrationRecord", foreign_keys=[authoritative_integration_id]
    )
    rules: Mapped[list["CorrelationRuleRecord"]] = relationship(
        "CorrelationRuleRecord",
        back_populates="policy",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CorrelationRuleRecord.priority",
    )


class CorrelationRuleRecord(Base):
    __tablename__ = "correlation_rules"
    __table_args__ = (
        UniqueConstraint("policy_id", "priority", name="uq_correlation_rule_policy_priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("correlation_policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    account_attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(String(40), nullable=False, default="EXACT")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    policy: Mapped[CorrelationPolicyRecord] = relationship(
        "CorrelationPolicyRecord", back_populates="rules"
    )
