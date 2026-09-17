"""remove orphan confidence

Revision ID: 20260914_0012
Revises: 20260914_0011
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_0012"
down_revision = "20260914_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("orphan_findings")}
    if "confidence" in columns:
        op.drop_column("orphan_findings", "confidence")


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("orphan_findings")}
    if "confidence" not in columns:
        op.add_column(
            "orphan_findings",
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        )
