"""Add notification_preferences to profile

Revision ID: 003
Revises: 002
Create Date: 2026-06-23 19:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profile",
        sa.Column("notification_preferences", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profile", "notification_preferences")
