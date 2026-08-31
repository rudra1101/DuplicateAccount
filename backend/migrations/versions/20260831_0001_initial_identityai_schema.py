"""Initial IdentityAI database schema.

Revision ID: 20260831_0001
Revises:
Create Date: 2026-08-31

This baseline revision creates the schema represented by the current
SQLAlchemy declarative metadata. It is intentionally used only as the initial
migration baseline; future revisions should use explicit Alembic operations.
"""

from __future__ import annotations

from alembic import op

import app.db_models  # noqa: F401
from app.database.base import Base


# revision identifiers, used by Alembic.
revision = "20260831_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
