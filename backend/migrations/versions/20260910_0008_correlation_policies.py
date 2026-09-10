"""Add configurable identity correlation policies.

Revision ID: 20260910_0008
Revises: 20260910_0007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260910_0008"
down_revision = "20260910_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "correlation_policies" not in tables:
        op.create_table(
            "correlation_policies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("account_integration_id", sa.Integer(), nullable=False),
            sa.Column("authoritative_integration_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("strategy", sa.String(length=40), nullable=False, server_default="FIRST_MATCH_WINS"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_integration_id"], ["integrations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["authoritative_integration_id"], ["integrations.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "account_integration_id",
                "authoritative_integration_id",
                "name",
                name="uq_correlation_policy_pair_name",
            ),
        )
        op.create_index("ix_correlation_policies_account_integration_id", "correlation_policies", ["account_integration_id"])
        op.create_index("ix_correlation_policies_authoritative_integration_id", "correlation_policies", ["authoritative_integration_id"])
        op.create_index("ix_correlation_policies_enabled", "correlation_policies", ["enabled"])

    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "correlation_rules" not in tables:
        op.create_table(
            "correlation_rules",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("policy_id", sa.Integer(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("account_attribute", sa.String(length=255), nullable=False),
            sa.Column("identity_attribute", sa.String(length=255), nullable=False),
            sa.Column("match_type", sa.String(length=40), nullable=False, server_default="EXACT"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["policy_id"], ["correlation_policies.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("policy_id", "priority", name="uq_correlation_rule_policy_priority"),
        )
        op.create_index("ix_correlation_rules_policy_id", "correlation_rules", ["policy_id"])
        op.create_index("ix_correlation_rules_enabled", "correlation_rules", ["enabled"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "correlation_rules" in tables:
        op.drop_table("correlation_rules")
    if "correlation_policies" in tables:
        op.drop_table("correlation_policies")
