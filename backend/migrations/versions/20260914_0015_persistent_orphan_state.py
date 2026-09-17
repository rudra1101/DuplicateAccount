"""add persistent orphan current state

Revision ID: 20260914_0015
Revises: 20260914_0014
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_0015"
down_revision = "20260914_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "orphan_states" in set(inspector.get_table_names()):
        return

    op.create_table(
        "orphan_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_account_id", sa.Integer(), sa.ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orphan_type", sa.String(length=50), nullable=False),
        sa.Column("correlation_method", sa.String(length=255), nullable=True),
        sa.Column("matched_identity_id", sa.Integer(), sa.ForeignKey("identities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_scan_id", sa.Integer(), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_account_id", name="uq_orphan_states_source_account"),
    )
    for column in ["integration_id", "source_account_id", "orphan_type", "matched_identity_id", "status", "active", "last_detected_at", "last_scan_id"]:
        op.create_index(f"ix_orphan_states_{column}", "orphan_states", [column])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "orphan_states" in set(inspector.get_table_names()):
        op.drop_table("orphan_states")
