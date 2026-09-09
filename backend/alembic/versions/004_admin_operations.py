"""Add admin analytics, audit context and calendar/report version metadata.

Revision ID: 004
Revises: 003
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_logs", sa.Column("target_user_id", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(length=500), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_target_user_id",
        "audit_logs",
        "users",
        ["target_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)

    op.add_column("user_calendars", sa.Column("series_id", sa.String(length=36), nullable=True))
    op.add_column("user_calendars", sa.Column("version_number", sa.Integer(), nullable=True, server_default="1"))
    op.execute("UPDATE user_calendars SET series_id = 'legacy-' || id::text WHERE series_id IS NULL")
    op.execute("UPDATE user_calendars SET version_number = 1 WHERE version_number IS NULL")
    op.alter_column("user_calendars", "series_id", nullable=False)
    op.alter_column("user_calendars", "version_number", nullable=False, server_default="1")
    op.create_index("ix_user_calendars_series_id", "user_calendars", ["series_id"], unique=False)
    op.create_unique_constraint(
        "uq_user_calendar_series_version",
        "user_calendars",
        ["series_id", "version_number"],
    )
    op.create_index(
        "uq_user_calendar_current_published",
        "user_calendars",
        ["series_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )

    op.add_column("report_tasks", sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("report_tasks", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("report_tasks", sa.Column("retry_of_task_id", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_report_tasks_retry_of_task_id",
        "report_tasks",
        "report_tasks",
        ["retry_of_task_id"],
        ["task_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_report_tasks_retry_of_task_id", "report_tasks", ["retry_of_task_id"], unique=False)


def downgrade():
    op.drop_index("ix_report_tasks_retry_of_task_id", table_name="report_tasks")
    op.drop_constraint("fk_report_tasks_retry_of_task_id", "report_tasks", type_="foreignkey")
    op.drop_column("report_tasks", "retry_of_task_id")
    op.drop_column("report_tasks", "retry_count")
    op.drop_column("report_tasks", "input_snapshot")

    op.drop_index("uq_user_calendar_current_published", table_name="user_calendars")
    op.drop_constraint("uq_user_calendar_series_version", "user_calendars", type_="unique")
    op.drop_index("ix_user_calendars_series_id", table_name="user_calendars")
    op.drop_column("user_calendars", "version_number")
    op.drop_column("user_calendars", "series_id")

    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_user_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_target_user_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "request_id")
    op.drop_column("audit_logs", "target_user_id")
