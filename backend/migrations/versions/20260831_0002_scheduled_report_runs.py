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


def upgrade() -> None:
    op.create_table(
        "scheduled_report_runs",
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
    op.create_index(
        op.f("ix_scheduled_report_runs_status"),
        "scheduled_report_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_report_runs_generated_at"),
        "scheduled_report_runs",
        ["generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_report_runs_generated_at"), table_name="scheduled_report_runs")
    op.drop_index(op.f("ix_scheduled_report_runs_status"), table_name="scheduled_report_runs")
    op.drop_table("scheduled_report_runs")
