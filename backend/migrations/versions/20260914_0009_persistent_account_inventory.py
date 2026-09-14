"""persistent account inventory and duplicate findings

Revision ID: 20260914_0009
Revises: 20260910_0008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260914_0009"
down_revision = "20260910_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "source_accounts" not in tables:
        op.create_table(
            "source_accounts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
            sa.Column("schema_id", sa.Integer(), sa.ForeignKey("application_schemas.id", ondelete="SET NULL"), nullable=True),
            sa.Column("application", sa.String(length=150), nullable=False),
            sa.Column("native_identity", sa.String(length=512), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=True),
            sa.Column("username", sa.String(length=255), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("employee_id", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=100), nullable=True),
            sa.Column("raw_attributes", sa.JSON(), nullable=False),
            sa.Column("attribute_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_scan_id", sa.Integer(), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("integration_id", "application", "native_identity", name="uq_source_accounts_integration_application_native"),
        )
        for column in ["integration_id", "application_id", "schema_id", "application", "native_identity", "username", "email", "employee_id", "status", "attribute_fingerprint", "active", "deleted", "last_seen_at", "last_scan_id"]:
            op.create_index(f"ix_source_accounts_{column}", "source_accounts", [column])

    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "duplicate_findings" not in tables:
        op.create_table(
            "duplicate_findings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("primary_source_account_id", sa.Integer(), sa.ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("duplicate_source_account_id", sa.Integer(), sa.ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_scan_id", sa.Integer(), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("integration_id", "primary_source_account_id", "duplicate_source_account_id", name="uq_duplicate_findings_pair"),
        )
        for column in ["integration_id", "primary_source_account_id", "duplicate_source_account_id", "status", "active", "last_detected_at", "last_scan_id"]:
            op.create_index(f"ix_duplicate_findings_{column}", "duplicate_findings", [column])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "duplicate_findings" in tables:
        op.drop_table("duplicate_findings")
    if "source_accounts" in tables:
        op.drop_table("source_accounts")
