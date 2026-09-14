"""remove orphan risk score and severity

Revision ID: 20260914_0011
Revises: 20260914_0010
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_0011"
down_revision = "20260914_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("orphan_findings")}
    indexes = {index["name"] for index in inspector.get_indexes("orphan_findings")}

    if "ix_orphan_findings_severity" in indexes:
        op.drop_index("ix_orphan_findings_severity", table_name="orphan_findings")
    if "severity" in columns:
        op.drop_column("orphan_findings", "severity")
    if "risk_score" in columns:
        op.drop_column("orphan_findings", "risk_score")


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("orphan_findings")}
    if "risk_score" not in columns:
        op.add_column("orphan_findings", sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"))
    if "severity" not in columns:
        op.add_column("orphan_findings", sa.Column("severity", sa.String(length=20), nullable=False, server_default="LOW"))

    inspector = inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("orphan_findings")}
    if "ix_orphan_findings_severity" not in indexes:
        op.create_index("ix_orphan_findings_severity", "orphan_findings", ["severity"], unique=False)
