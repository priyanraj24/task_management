"""add updated_at columns

Revision ID: 007
Revises: 006
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ["users", "projects", "tasks"]:
        op.add_column(table, sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True))


def downgrade() -> None:
    for table in ["users", "projects", "tasks"]:
        op.drop_column(table, "updated_at")
