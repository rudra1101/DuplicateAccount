"""add authoritative identity state for full and delta aggregation

Revision ID: 20260914_0014
Revises: 20260914_0013
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_0014"
down_revision = "20260914_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("identities")}

    if "active" not in columns:
        op.add_column("identities", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "deleted" not in columns:
        op.add_column("identities", sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "first_seen_at" not in columns:
        op.add_column("identities", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))
        op.execute("UPDATE identities SET first_seen_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE first_seen_at IS NULL")
        op.alter_column("identities", "first_seen_at", nullable=False)
    if "last_seen_at" not in columns:
        op.add_column("identities", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        op.execute("UPDATE identities SET last_seen_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE last_seen_at IS NULL")
        op.alter_column("identities", "last_seen_at", nullable=False)

    inspector = inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("identities")}
    if "ix_identities_active" not in indexes:
        op.create_index("ix_identities_active", "identities", ["active"])
    if "ix_identities_deleted" not in indexes:
        op.create_index("ix_identities_deleted", "identities", ["deleted"])
    if "ix_identities_last_seen_at" not in indexes:
        op.create_index("ix_identities_last_seen_at", "identities", ["last_seen_at"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("identities")}
    for name in ["ix_identities_last_seen_at", "ix_identities_deleted", "ix_identities_active"]:
        if name in indexes:
            op.drop_index(name, table_name="identities")

    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("identities")}
    for name in ["last_seen_at", "first_seen_at", "deleted", "active"]:
        if name in columns:
            op.drop_column("identities", name)
