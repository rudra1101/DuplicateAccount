"""Add authoritative identities and orphan account findings.

Revision ID: 20260910_0007
Revises: 20260901_0006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260910_0007"
down_revision = "20260901_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "integrations" in tables:
        columns = {column["name"] for column in inspector.get_columns("integrations")}
        if "source_purpose" not in columns:
            with op.batch_alter_table("integrations") as batch:
                batch.add_column(
                    sa.Column(
                        "source_purpose",
                        sa.String(length=30),
                        nullable=False,
                        server_default="ACCOUNT",
                    )
                )
                batch.create_index("ix_integrations_source_purpose", ["source_purpose"])

    if "identities" not in tables:
        op.create_table(
            "identities",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("integration_id", sa.Integer(), nullable=False),
            sa.Column("source_identity_id", sa.String(length=255), nullable=False),
            sa.Column("employee_id", sa.String(length=100), nullable=True),
            sa.Column("username", sa.String(length=255), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("display_name", sa.String(length=255), nullable=True),
            sa.Column("department", sa.String(length=150), nullable=True),
            sa.Column("manager", sa.String(length=255), nullable=True),
            sa.Column("employment_status", sa.String(length=50), nullable=True),
            sa.Column("raw_attributes", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "integration_id",
                "source_identity_id",
                name="uq_identities_integration_source_identity",
            ),
        )
        op.create_index("ix_identities_integration_id", "identities", ["integration_id"])
        op.create_index("ix_identities_employee_id", "identities", ["employee_id"])
        op.create_index("ix_identities_username", "identities", ["username"])
        op.create_index("ix_identities_email", "identities", ["email"])
        op.create_index("ix_identities_employment_status", "identities", ["employment_status"])

    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "orphan_findings" not in tables:
        op.create_table(
            "orphan_findings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("scan_id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("finding_type", sa.String(length=50), nullable=False),
            sa.Column("orphan_type", sa.String(length=50), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("risk_score", sa.Float(), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("correlation_method", sa.String(length=50), nullable=True),
            sa.Column("matched_identity_id", sa.Integer(), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["matched_identity_id"], ["identities.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("scan_id", "account_id", name="uq_orphan_findings_scan_account"),
        )
        op.create_index("ix_orphan_findings_scan_id", "orphan_findings", ["scan_id"])
        op.create_index("ix_orphan_findings_account_id", "orphan_findings", ["account_id"])
        op.create_index("ix_orphan_findings_finding_type", "orphan_findings", ["finding_type"])
        op.create_index("ix_orphan_findings_orphan_type", "orphan_findings", ["orphan_type"])
        op.create_index("ix_orphan_findings_severity", "orphan_findings", ["severity"])
        op.create_index("ix_orphan_findings_matched_identity_id", "orphan_findings", ["matched_identity_id"])
        op.create_index("ix_orphan_findings_status", "orphan_findings", ["status"])
        op.create_index("ix_orphan_findings_created_at", "orphan_findings", ["created_at"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "orphan_findings" in tables:
        op.drop_table("orphan_findings")
    if "identities" in tables:
        op.drop_table("identities")
    if "integrations" in tables:
        columns = {column["name"] for column in inspector.get_columns("integrations")}
        if "source_purpose" in columns:
            with op.batch_alter_table("integrations") as batch:
                batch.drop_index("ix_integrations_source_purpose")
                batch.drop_column("source_purpose")
