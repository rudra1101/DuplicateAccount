"""persist Rudrix Agent Core conversation state

Revision ID: 20261008_0019
Revises: 20260917_0018
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261008_0019"
down_revision = "20260917_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("chat_conversations")
    }
    if "agent_state" in columns:
        return

    op.add_column(
        "chat_conversations",
        sa.Column(
            "agent_state",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("chat_conversations")
    }
    if "agent_state" in columns:
        op.drop_column("chat_conversations", "agent_state")
