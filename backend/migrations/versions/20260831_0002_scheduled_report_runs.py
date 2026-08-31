"""Add scheduled report run history.

Revision ID: 20260831_0002
Revises: 20260831_0001
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260831_0002"
down_revision = "20260831_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    table_name = "scheduled_report_runs"
    status_index = op.f("ix_scheduled_report_runs_status")
    generated_index = op.f("ix_scheduled_report_runs_generated_at")

    # The original 0001 baseline used Base.metadata.create_all(). On a fresh
    # install with newer models loaded, that baseline can already create this
    # table before Alembic reaches 0002. Keep this migration compatible with
    # both fresh installs and databases that were previously stamped at 0001.
    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("report_name", sa.String(length=150), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("test_mode", sa.Boolean(), nullable=False),
            sa.Column("recipients", sa.JSON(), nullable=False),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("row_count", sa.Integer(), nullable=False),
            sa.Column("csv_content", sa.Text(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(table_name, status_index):
        op.create_index(status_index, table_name, ["status"], unique=False)

    if not _index_exists(table_name, generated_index):
        op.create_index(generated_index, table_name, ["generated_at"], unique=False)


def downgrade() -> None:
    table_name = "scheduled_report_runs"
    if not _table_exists(table_name):
        return

    generated_index = op.f("ix_scheduled_report_runs_generated_at")
    status_index = op.f("ix_scheduled_report_runs_status")

    if _index_exists(table_name, generated_index):
        op.drop_index(generated_index, table_name=table_name)
    if _index_exists(table_name, status_index):
        op.drop_index(status_index, table_name=table_name)

    op.drop_table(table_name)
