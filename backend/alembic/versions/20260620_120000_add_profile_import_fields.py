"""Add profile-import fields and curriculum_vitae table.

Revision ID: 002
Revises: 001
Create Date: 2026-06-20 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- profile: add new columns ---
    op.add_column("profile", sa.Column("headline", sa.String(500), nullable=True))
    op.add_column("profile", sa.Column("summary", sa.String(), nullable=True))
    op.add_column("profile", sa.Column("skills", postgresql.JSON(), nullable=True))
    op.add_column("profile", sa.Column("education", postgresql.JSON(), nullable=True))
    op.add_column("profile", sa.Column("work_experience", postgresql.JSON(), nullable=True))
    op.add_column("profile", sa.Column("linkedin_url", sa.String(500), nullable=True))
    op.add_column("profile", sa.Column("infojobs_url", sa.String(500), nullable=True))
    op.add_column("profile", sa.Column("cv_file_url", sa.String(500), nullable=True))

    # --- curriculum_vitae table ---
    op.create_table(
        "curriculum_vitae",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("parsed_data", postgresql.JSON(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_curriculum_vitae_user",
        "curriculum_vitae",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_table("curriculum_vitae")
    op.drop_column("profile", "cv_file_url")
    op.drop_column("profile", "infojobs_url")
    op.drop_column("profile", "linkedin_url")
    op.drop_column("profile", "work_experience")
    op.drop_column("profile", "education")
    op.drop_column("profile", "skills")
    op.drop_column("profile", "summary")
    op.drop_column("profile", "headline")
