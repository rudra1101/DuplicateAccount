"""Add application settings for SMTP and branding.

Revision ID: 20260901_0003
Revises: 20260831_0002
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260901_0003"
down_revision = "20260831_0002"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    table_name = "application_settings"

    # The 0001 baseline uses Base.metadata.create_all(), so a fresh database
    # running newer application models may already contain this table before
    # Alembic reaches this revision. Keep the migration safe in both cases.
    if _table_exists(table_name):
        return

    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("smtp_enabled", sa.Boolean(), nullable=False),
        sa.Column("smtp_host", sa.String(length=255), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False),
        sa.Column("smtp_username", sa.String(length=255), nullable=False),
        sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
        sa.Column("smtp_from_email", sa.String(length=320), nullable=False),
        sa.Column("smtp_use_tls", sa.Boolean(), nullable=False),
        sa.Column("logo_filename", sa.String(length=255), nullable=True),
        sa.Column("logo_mime_type", sa.String(length=100), nullable=True),
        sa.Column("logo_data", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    if _table_exists("application_settings"):
        op.drop_table("application_settings")
