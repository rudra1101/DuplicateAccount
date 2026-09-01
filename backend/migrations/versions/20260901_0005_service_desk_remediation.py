"""Add service desk configuration and remediation ticket tracking.

Revision ID: 20260901_0005
Revises: 20260901_0004
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260901_0005"
down_revision = "20260901_0004"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        column.get("name") == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    settings = "application_settings"
    _add_column_if_missing(settings, sa.Column("service_desk_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing(settings, sa.Column("service_desk_name", sa.String(length=150), nullable=False, server_default="Service Desk"))
    _add_column_if_missing(settings, sa.Column("service_desk_base_url", sa.String(length=1000), nullable=False, server_default=""))
    _add_column_if_missing(settings, sa.Column("service_desk_auth_type", sa.String(length=20), nullable=False, server_default="BEARER"))
    _add_column_if_missing(settings, sa.Column("service_desk_username", sa.String(length=255), nullable=False, server_default=""))
    _add_column_if_missing(settings, sa.Column("service_desk_secret_encrypted", sa.Text(), nullable=True))
    _add_column_if_missing(settings, sa.Column("service_desk_create_path", sa.String(length=1000), nullable=False, server_default="/tickets"))
    _add_column_if_missing(settings, sa.Column("service_desk_status_path", sa.String(length=1000), nullable=False, server_default="/tickets/{ticket_id}"))
    _add_column_if_missing(settings, sa.Column("service_desk_ticket_id_field", sa.String(length=255), nullable=False, server_default="id"))
    _add_column_if_missing(settings, sa.Column("service_desk_ticket_status_field", sa.String(length=255), nullable=False, server_default="status"))
    _add_column_if_missing(settings, sa.Column("service_desk_ticket_url_field", sa.String(length=255), nullable=False, server_default="url"))
    _add_column_if_missing(settings, sa.Column("service_desk_completed_statuses", sa.String(length=500), nullable=False, server_default="completed,resolved,closed"))
    _add_column_if_missing(settings, sa.Column("service_desk_payload_template", sa.Text(), nullable=False, server_default='{"summary":"{{summary}}","description":"{{description}}","action":"{{action}}","accountKey":"{{account_key}}","application":"{{application}}"}'))
    _add_column_if_missing(settings, sa.Column("service_desk_verify_tls", sa.Boolean(), nullable=False, server_default=sa.true()))

    remediation = "remediation_items"
    _add_column_if_missing(remediation, sa.Column("remediation_action", sa.String(length=20), nullable=True))
    _add_column_if_missing(remediation, sa.Column("target_account_key", sa.String(length=500), nullable=True))
    _add_column_if_missing(remediation, sa.Column("service_desk_ticket_id", sa.String(length=255), nullable=True))
    _add_column_if_missing(remediation, sa.Column("service_desk_ticket_status", sa.String(length=100), nullable=True))
    _add_column_if_missing(remediation, sa.Column("service_desk_ticket_url", sa.String(length=2000), nullable=True))
    _add_column_if_missing(remediation, sa.Column("ticket_created_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(remediation, sa.Column("ticket_last_synced_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(remediation, sa.Column("ticket_error", sa.Text(), nullable=True))


def downgrade() -> None:
    remediation_columns = [
        "ticket_error", "ticket_last_synced_at", "ticket_created_at",
        "service_desk_ticket_url", "service_desk_ticket_status", "service_desk_ticket_id",
        "target_account_key", "remediation_action",
    ]
    for name in remediation_columns:
        if _column_exists("remediation_items", name):
            op.drop_column("remediation_items", name)

    setting_columns = [
        "service_desk_verify_tls", "service_desk_payload_template", "service_desk_completed_statuses",
        "service_desk_ticket_url_field", "service_desk_ticket_status_field", "service_desk_ticket_id_field",
        "service_desk_status_path", "service_desk_create_path", "service_desk_secret_encrypted",
        "service_desk_username", "service_desk_auth_type", "service_desk_base_url",
        "service_desk_name", "service_desk_enabled",
    ]
    for name in setting_columns:
        if _column_exists("application_settings", name):
            op.drop_column("application_settings", name)
