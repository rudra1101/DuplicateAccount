"""Add per-user ownership to chat conversations.

Revision ID: 20260917_0017
Revises: 20260915_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260917_0017"
down_revision = "20260915_0016"
branch_labels = None
depends_on = None


def _columns(bind) -> set[str]:
    inspector = sa.inspect(bind)
    if "chat_conversations" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("chat_conversations")}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind)
    if not columns:
        return

    if "user_id" not in columns:
        op.add_column(
            "chat_conversations",
            sa.Column("user_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_chat_conversations_user_id_users",
            "chat_conversations",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            "ix_chat_conversations_user_id",
            "chat_conversations",
            ["user_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind)
    if "user_id" not in columns:
        return

    op.drop_index(
        "ix_chat_conversations_user_id",
        table_name="chat_conversations",
    )
    op.drop_constraint(
        "fk_chat_conversations_user_id_users",
        "chat_conversations",
        type_="foreignkey",
    )
    op.drop_column("chat_conversations", "user_id")
