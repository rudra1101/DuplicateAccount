"""remove orphan risk score and severity

Revision ID: 20260914_0011
Revises: 20260914_0010
"""

from alembic import op
import sqlalchemy as sa

revision = "20260914_0011"
down_revision = "20260914_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_orphan_findings_severity", table_name="orphan_findings")
    op.drop_column("orphan_findings", "severity")
    op.drop_column("orphan_findings", "risk_score")


def downgrade() -> None:
    op.add_column("orphan_findings", sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orphan_findings", sa.Column("severity", sa.String(length=20), nullable=False, server_default="LOW"))
    op.create_index("ix_orphan_findings_severity", "orphan_findings", ["severity"], unique=False)
