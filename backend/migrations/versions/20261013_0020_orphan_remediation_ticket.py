"""Track Service Desk remediation tickets on current orphan state.

Revision ID: 20261013_0020
Revises: 20261008_0019
"""

from alembic import op
import sqlalchemy as sa


revision = "20261013_0020"
down_revision = "20261008_0019"
branch_labels = None
depends_on = None


_COLUMNS = (
    sa.Column("remediation_action", sa.String(length=20), nullable=True),
    sa.Column("actioned_by", sa.String(length=255), nullable=True),
    sa.Column("service_desk_ticket_id", sa.String(length=255), nullable=True),
    sa.Column("service_desk_ticket_status", sa.String(length=100), nullable=True),
    sa.Column("service_desk_ticket_url", sa.String(length=2000), nullable=True),
    sa.Column("ticket_created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("ticket_last_synced_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("ticket_error", sa.Text(), nullable=True),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "orphan_states" not in set(inspector.get_table_names()):
        return

    existing = {column["name"] for column in inspector.get_columns("orphan_states")}
    for column in _COLUMNS:
        if column.name not in existing:
            op.add_column("orphan_states", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "orphan_states" not in set(inspector.get_table_names()):
        return

    existing = {column["name"] for column in inspector.get_columns("orphan_states")}
    for column in reversed(_COLUMNS):
        if column.name in existing:
            op.drop_column("orphan_states", column.name)
