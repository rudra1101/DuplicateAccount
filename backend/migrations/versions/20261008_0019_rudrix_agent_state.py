"""Persist Rudrix structured agent state on chat conversations.

Revision ID: 20261008_0019
Revises: 20260917_0018
"""

from alembic import op
import sqlalchemy as sa


revision = "20261008_0019"
down_revision = "20260917_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "chat_conversations" not in tables:
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("chat_conversations")
    }
    if "agent_state" not in columns:
        op.add_column(
            "chat_conversations",
            sa.Column("agent_state", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "chat_conversations" not in tables:
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("chat_conversations")
    }
    if "agent_state" in columns:
        op.drop_column("chat_conversations", "agent_state")
