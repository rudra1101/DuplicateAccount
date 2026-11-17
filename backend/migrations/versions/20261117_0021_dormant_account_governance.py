"""Add normalized last-login and dormant-account remediation state.

Revision ID: 20261117_0021
Revises: 20261013_0020
"""

from alembic import op
import sqlalchemy as sa


revision = "20261117_0021"
down_revision = "20261013_0020"
branch_labels = None
depends_on = None


_COLUMNS = (
    sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_dormancy_reminder_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("dormancy_ticket_id", sa.String(length=255), nullable=True),
    sa.Column("dormancy_ticket_status", sa.String(length=100), nullable=True),
    sa.Column("dormancy_ticket_url", sa.String(length=2000), nullable=True),
    sa.Column("dormancy_ticket_created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("dormancy_ticket_last_synced_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("dormancy_ticket_error", sa.Text(), nullable=True),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "source_accounts" not in set(inspector.get_table_names()):
        return

    existing = {column["name"] for column in inspector.get_columns("source_accounts")}
    for column in _COLUMNS:
        if column.name not in existing:
            op.add_column("source_accounts", column)

    indexes = {index["name"] for index in inspector.get_indexes("source_accounts")}
    if "ix_source_accounts_last_login_at" not in indexes:
        op.create_index(
            "ix_source_accounts_last_login_at",
            "source_accounts",
            ["last_login_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "source_accounts" not in set(inspector.get_table_names()):
        return

    indexes = {index["name"] for index in inspector.get_indexes("source_accounts")}
    if "ix_source_accounts_last_login_at" in indexes:
        op.drop_index("ix_source_accounts_last_login_at", table_name="source_accounts")

    existing = {column["name"] for column in inspector.get_columns("source_accounts")}
    for column in reversed(_COLUMNS):
        if column.name in existing:
            op.drop_column("source_accounts", column.name)
