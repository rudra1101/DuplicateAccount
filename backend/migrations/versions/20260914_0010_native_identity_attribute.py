"""add native identity attribute to application schemas

Revision ID: 20260914_0010
Revises: 20260914_0009
"""

from alembic import op
import sqlalchemy as sa


revision = "20260914_0010"
down_revision = "20260914_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_schemas",
        sa.Column("native_identity_attribute", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application_schemas", "native_identity_attribute")
