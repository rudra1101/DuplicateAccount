"""Add reusable report email templates.

Revision ID: 20260901_0004
Revises: 20260901_0003
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260901_0004"
down_revision = "20260901_0003"
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


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        index.get("name") == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def upgrade() -> None:
    table_name = "report_email_templates"
    name_index = op.f("ix_report_email_templates_name")

    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("subject_template", sa.String(length=300), nullable=False),
            sa.Column("text_body_template", sa.Text(), nullable=False),
            sa.Column("html_body_template", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if not _index_exists(table_name, name_index):
        op.create_index(name_index, table_name, ["name"], unique=True)

    if not _column_exists("scheduled_report_config", "email_template_id"):
        op.add_column(
            "scheduled_report_config",
            sa.Column("email_template_id", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("scheduled_report_config", "email_template_id"):
        op.drop_column("scheduled_report_config", "email_template_id")

    table_name = "report_email_templates"
    if _table_exists(table_name):
        name_index = op.f("ix_report_email_templates_name")
        if _index_exists(table_name, name_index):
            op.drop_index(name_index, table_name=table_name)
        op.drop_table(table_name)
