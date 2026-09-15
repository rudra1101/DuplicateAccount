"""Add global branding color palette.

Revision ID: 0016
Revises: 0015
"""

from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


DEFAULTS = {
    "branding_primary_color": "#1565C0",
    "branding_secondary_color": "#1976D2",
    "branding_navigation_color": "#0F172A",
    "branding_background_color": "#F5F7FA",
}


def _column_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    if "application_settings" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("application_settings")}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _column_names(bind)
    if not existing:
        return

    for name, default in DEFAULTS.items():
        if name not in existing:
            op.add_column(
                "application_settings",
                sa.Column(name, sa.String(length=7), nullable=False, server_default=default),
            )



def downgrade() -> None:
    bind = op.get_bind()
    existing = _column_names(bind)
    for name in reversed(list(DEFAULTS)):
        if name in existing:
            op.drop_column("application_settings", name)
