"""add aggregation mode and inventory change counts

Revision ID: 20260914_0013
Revises: 20260914_0012
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_0013"
down_revision = "20260914_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("job_executions")}
    with op.batch_alter_table("job_executions") as batch:
        if "aggregation_type" not in columns:
            batch.add_column(sa.Column("aggregation_type", sa.String(length=20), nullable=False, server_default="FULL"))
        if "accounts_created" not in columns:
            batch.add_column(sa.Column("accounts_created", sa.Integer(), nullable=False, server_default="0"))
        if "accounts_updated" not in columns:
            batch.add_column(sa.Column("accounts_updated", sa.Integer(), nullable=False, server_default="0"))
        if "accounts_unchanged" not in columns:
            batch.add_column(sa.Column("accounts_unchanged", sa.Integer(), nullable=False, server_default="0"))
        if "accounts_deleted" not in columns:
            batch.add_column(sa.Column("accounts_deleted", sa.Integer(), nullable=False, server_default="0"))

    inspector = inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("job_executions")}
    if "ix_job_executions_aggregation_type" not in indexes:
        op.create_index("ix_job_executions_aggregation_type", "job_executions", ["aggregation_type"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("job_executions")}
    if "ix_job_executions_aggregation_type" in indexes:
        op.drop_index("ix_job_executions_aggregation_type", table_name="job_executions")

    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("job_executions")}
    with op.batch_alter_table("job_executions") as batch:
        for name in ["accounts_deleted", "accounts_unchanged", "accounts_updated", "accounts_created", "aggregation_type"]:
            if name in columns:
                batch.drop_column(name)
