"""add soft delete columns

Revision ID: 005
Revises: 004
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ["users", "projects", "tasks", "task_history", "attachments"]:
        op.add_column(table, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table in ["users", "projects", "tasks", "task_history", "attachments"]:
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "is_deleted")
