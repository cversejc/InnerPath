"""Add reusable profiles and user-owned calendar requests.

Revision ID: 005
Revises: 004
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _jsonb_list_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )


def upgrade():
    op.add_column("users", sa.Column("calendar_type", sa.String(length=10), nullable=False, server_default="solar"))
    op.add_column("users", sa.Column("birth_time_precision", sa.String(length=20), nullable=False, server_default="unknown"))
    op.add_column("users", sa.Column("current_residence", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("marital_status", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("occupation_status", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("highest_education", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("mbti", sa.String(length=10), nullable=True))
    op.add_column("users", _jsonb_list_column("personality_keywords"))
    op.add_column("users", sa.Column("strengths", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("limitations", sa.Text(), nullable=True))
    op.add_column("users", _jsonb_list_column("mingli_experience"))
    op.add_column("users", sa.Column("mingli_attitude", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("preferred_content_depth", sa.String(length=30), nullable=True))
    op.add_column("users", _jsonb_list_column("default_usage_scenarios"))
    op.add_column("users", sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("profile_last_confirmed_at", sa.DateTime(), nullable=True))
    # Legacy profiles had no precision flag. Preserve the fact that a complete
    # legacy time was supplied without claiming it was exact.
    op.execute(
        "UPDATE users SET birth_time_precision = 'approximate' "
        "WHERE birth_hour IS NOT NULL AND birth_minute IS NOT NULL"
    )

    op.create_table(
        "calendar_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_report_id", sa.Integer(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("focus_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("usage_scenario", sa.String(length=50), nullable=True),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("decision_description", sa.Text(), nullable=True),
        sa.Column("expected_outcomes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("additional_info", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_requests_user_id", "calendar_requests", ["user_id"], unique=False)
    op.create_index("ix_calendar_requests_source_report_id", "calendar_requests", ["source_report_id"], unique=False)
    op.create_index("ix_calendar_requests_status", "calendar_requests", ["status"], unique=False)

    op.add_column("user_calendars", sa.Column("calendar_request_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_user_calendars_calendar_request_id",
        "user_calendars",
        "calendar_requests",
        ["calendar_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_user_calendars_calendar_request_id", "user_calendars", ["calendar_request_id"], unique=False)


def downgrade():
    op.drop_index("ix_user_calendars_calendar_request_id", table_name="user_calendars")
    op.drop_constraint("fk_user_calendars_calendar_request_id", "user_calendars", type_="foreignkey")
    op.drop_column("user_calendars", "calendar_request_id")

    op.drop_index("ix_calendar_requests_status", table_name="calendar_requests")
    op.drop_index("ix_calendar_requests_source_report_id", table_name="calendar_requests")
    op.drop_index("ix_calendar_requests_user_id", table_name="calendar_requests")
    op.drop_table("calendar_requests")

    for column in (
        "profile_last_confirmed_at",
        "profile_version",
        "default_usage_scenarios",
        "preferred_content_depth",
        "mingli_attitude",
        "mingli_experience",
        "limitations",
        "strengths",
        "personality_keywords",
        "mbti",
        "highest_education",
        "occupation_status",
        "marital_status",
        "current_residence",
        "birth_time_precision",
        "calendar_type",
    ):
        op.drop_column("users", column)
