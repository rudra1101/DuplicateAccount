"""Assign legacy unowned chat conversations to the Admin user.

Revision ID: 20260917_0018
Revises: 20260917_0017
"""

from alembic import op
import sqlalchemy as sa


revision = "20260917_0018"
down_revision = "20260917_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "chat_conversations" not in tables or "users" not in tables:
        return

    conversation_columns = {
        column["name"]
        for column in inspector.get_columns("chat_conversations")
    }
    if "user_id" not in conversation_columns:
        return

    # Prefer the conventional username "admin" when it exists. If this
    # installation uses another username for the ADMIN role, fall back to
    # the oldest active ADMIN account so the backfill is deterministic.
    admin_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM users
            WHERE is_active = true
              AND lower(username) = 'admin'
            ORDER BY id ASC
            LIMIT 1
            """
        )
    ).scalar()

    if admin_id is None:
        admin_id = bind.execute(
            sa.text(
                """
                SELECT id
                FROM users
                WHERE is_active = true
                  AND upper(role) = 'ADMIN'
                ORDER BY id ASC
                LIMIT 1
                """
            )
        ).scalar()

    if admin_id is None:
        # No suitable Admin account exists yet. Leave legacy rows unowned;
        # the ownership checks introduced in 0017 keep them hidden.
        return

    bind.execute(
        sa.text(
            """
            UPDATE chat_conversations
            SET user_id = :admin_id
            WHERE user_id IS NULL
            """
        ),
        {"admin_id": int(admin_id)},
    )


def downgrade() -> None:
    # This migration is a data ownership backfill. Reverting it would make
    # previously protected conversations globally unowned again, so the
    # downgrade intentionally preserves ownership assignments.
    pass
