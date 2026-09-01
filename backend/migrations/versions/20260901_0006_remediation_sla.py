"""Add remediation SLA configuration and tracking.

Revision ID: 20260901_0006
Revises: 20260901_0005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260901_0006"
down_revision = "20260901_0005"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "application_settings" in tables:
        existing = _columns("application_settings")
        with op.batch_alter_table("application_settings") as batch:
            if "remediation_sla_enabled" not in existing:
                batch.add_column(sa.Column("remediation_sla_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
            if "remediation_sla_hours" not in existing:
                batch.add_column(sa.Column("remediation_sla_hours", sa.Integer(), nullable=False, server_default="72"))
            if "remediation_warning_hours" not in existing:
                batch.add_column(sa.Column("remediation_warning_hours", sa.Integer(), nullable=False, server_default="24"))
            if "remediation_auto_escalate" not in existing:
                batch.add_column(sa.Column("remediation_auto_escalate", sa.Boolean(), nullable=False, server_default=sa.true()))
            if "remediation_escalation_emails" not in existing:
                batch.add_column(sa.Column("remediation_escalation_emails", sa.Text(), nullable=False, server_default=""))

    if "remediation_items" in tables:
        existing = _columns("remediation_items")
        with op.batch_alter_table("remediation_items") as batch:
            if "sla_due_at" not in existing:
                batch.add_column(sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True))
                batch.create_index("ix_remediation_items_sla_due_at", ["sla_due_at"], unique=False)
            if "sla_escalated_at" not in existing:
                batch.add_column(sa.Column("sla_escalated_at", sa.DateTime(timezone=True), nullable=True))
            if "sla_notification_sent_at" not in existing:
                batch.add_column(sa.Column("sla_notification_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "remediation_items" in tables:
        existing = _columns("remediation_items")
        with op.batch_alter_table("remediation_items") as batch:
            if "sla_notification_sent_at" in existing:
                batch.drop_column("sla_notification_sent_at")
            if "sla_escalated_at" in existing:
                batch.drop_column("sla_escalated_at")
            if "sla_due_at" in existing:
                try:
                    batch.drop_index("ix_remediation_items_sla_due_at")
                except Exception:
                    pass
                batch.drop_column("sla_due_at")

    if "application_settings" in tables:
        existing = _columns("application_settings")
        with op.batch_alter_table("application_settings") as batch:
            for column in (
                "remediation_escalation_emails",
                "remediation_auto_escalate",
                "remediation_warning_hours",
                "remediation_sla_hours",
                "remediation_sla_enabled",
            ):
                if column in existing:
                    batch.drop_column(column)
