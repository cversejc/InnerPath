"""Track report-driven calendar generation and source report provenance.

Revision ID: 010
Revises: 009
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_requests", sa.Column("task_id", sa.String(length=64), nullable=True))
    op.add_column(
        "calendar_requests",
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("calendar_requests", sa.Column("generation_error", sa.Text(), nullable=True))
    op.add_column(
        "calendar_requests",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_calendar_requests_task_id", "calendar_requests", ["task_id"])

    op.add_column(
        "user_calendars",
        sa.Column("source_report_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_calendars_source_report_id_reports",
        "user_calendars",
        "reports",
        ["source_report_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_user_calendars_source_report_id",
        "user_calendars",
        ["source_report_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_calendars_source_report_id", table_name="user_calendars")
    op.drop_constraint(
        "fk_user_calendars_source_report_id_reports",
        "user_calendars",
        type_="foreignkey",
    )
    op.drop_column("user_calendars", "source_report_id")
    op.drop_index("ix_calendar_requests_task_id", table_name="calendar_requests")
    op.drop_column("calendar_requests", "retry_count")
    op.drop_column("calendar_requests", "generation_error")
    op.drop_column("calendar_requests", "progress")
    op.drop_column("calendar_requests", "task_id")
