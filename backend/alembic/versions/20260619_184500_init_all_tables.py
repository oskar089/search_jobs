"""Initial migration — create all 8 tables.

Revision ID: 001
Revises:
Create Date: 2026-06-19 18:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- user ---
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- profile ---
    op.create_table(
        "profile",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), unique=True, nullable=False),
        sa.Column("target_roles", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("tech_stack", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("experience_level", sa.String(50), nullable=False),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("max_salary", sa.Integer(), nullable=True),
        sa.Column("locations", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("remote_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("languages", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_profile_user", "profile", "user", ["user_id"], ["id"], ondelete="CASCADE"
    )

    # --- portal ---
    op.create_table(
        "portal",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("job_listing_url", sa.String(500), nullable=False),
        sa.Column("selectors", postgresql.JSON(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scrape_interval_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_portal_user", "portal", "user", ["user_id"], ["id"], ondelete="SET NULL"
    )

    # --- stored_job ---
    op.create_table(
        "stored_job",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("portal_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("salary_range", sa.String(255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
    )
    op.create_foreign_key(
        "fk_stored_job_portal", "stored_job", "portal", ["portal_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint(
        "uq_portal_external_job", "stored_job", ["portal_id", "external_id"]
    )

    # --- scrape_session ---
    op.create_table(
        "scrape_session",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("portal_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_scrape_session_portal",
        "scrape_session",
        "portal",
        ["portal_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- pipeline_run ---
    op.create_table(
        "pipeline_run",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("portal_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("trigger", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("steps", postgresql.JSON(), nullable=True),
        sa.Column("error_step", sa.String(50), nullable=True),
        sa.Column("error_msg", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_pipeline_run_user",
        "pipeline_run",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- application ---
    op.create_table(
        "application",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("stored_job_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("cover_letter_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cover_letter_text", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_application_user",
        "application",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_application_stored_job",
        "application",
        "stored_job",
        ["stored_job_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_application_pipeline_run",
        "application",
        "pipeline_run",
        ["pipeline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- notification ---
    op.create_table(
        "notification",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_notification_user",
        "notification",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_notification_application",
        "notification",
        "application",
        ["application_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("notification")
    op.drop_table("application")
    op.drop_table("pipeline_run")
    op.drop_table("scrape_session")
    op.drop_table("stored_job")
    op.drop_table("portal")
    op.drop_table("profile")
    op.drop_table("user")
