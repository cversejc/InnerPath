"""Add consultant-assisted service requests and private AI drafts.

Revision ID: 007
Revises: 006
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "service_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="submitted"),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("assigned_consultant_id", sa.Integer(), nullable=True),
        sa.Column("result_type", sa.String(length=20), nullable=True),
        sa.Column("result_id", sa.Integer(), nullable=True),
        sa.Column("needs_info_reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("ai_started_at", sa.DateTime(), nullable=True),
        sa.Column("ai_completed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewing_at", sa.DateTime(), nullable=True),
        sa.Column("needs_info_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_consultant_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_service_request_user_idempotency"),
    )
    op.create_index("ix_service_requests_user_id", "service_requests", ["user_id"], unique=False)
    op.create_index("ix_service_requests_service_type", "service_requests", ["service_type"], unique=False)
    op.create_index("ix_service_requests_status", "service_requests", ["status"], unique=False)
    op.create_index("ix_service_requests_assigned_consultant_id", "service_requests", ["assigned_consultant_id"], unique=False)

    op.create_table(
        "service_request_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("ai_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("editable_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_request_drafts_request_id", "service_request_drafts", ["request_id"], unique=True)

    op.create_table(
        "service_request_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "version_number", name="uq_service_request_revision_version"),
    )
    op.create_index("ix_service_request_revisions_request_id", "service_request_revisions", ["request_id"], unique=False)

    op.create_table(
        "service_request_tasks",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="processing"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_of_task_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retry_of_task_id"], ["service_request_tasks.task_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index("ix_service_request_tasks_request_id", "service_request_tasks", ["request_id"], unique=False)
    op.create_index("ix_service_request_tasks_service_type", "service_request_tasks", ["service_type"], unique=False)
    op.create_index("ix_service_request_tasks_status", "service_request_tasks", ["status"], unique=False)
    op.create_index("ix_service_request_tasks_retry_of_task_id", "service_request_tasks", ["retry_of_task_id"], unique=False)

    op.add_column("reports", sa.Column("request_id", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("content_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("reports", sa.Column("reviewed_by", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_reports_request_id", "reports", "service_requests", ["request_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_reports_reviewed_by", "reports", "users", ["reviewed_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_reports_request_id", "reports", ["request_id"], unique=False)

    op.add_column("user_calendars", sa.Column("meta_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("user_calendars", sa.Column("request_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_user_calendars_request_id", "user_calendars", "service_requests", ["request_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_user_calendars_request_id", "user_calendars", ["request_id"], unique=False)


def downgrade():
    op.drop_index("ix_user_calendars_request_id", table_name="user_calendars")
    op.drop_constraint("fk_user_calendars_request_id", "user_calendars", type_="foreignkey")
    op.drop_column("user_calendars", "request_id")
    op.drop_column("user_calendars", "meta_payload")

    op.drop_index("ix_reports_request_id", table_name="reports")
    op.drop_constraint("fk_reports_reviewed_by", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_request_id", "reports", type_="foreignkey")
    op.drop_column("reports", "reviewed_at")
    op.drop_column("reports", "reviewed_by")
    op.drop_column("reports", "content_payload")
    op.drop_column("reports", "request_id")

    op.drop_index("ix_service_request_tasks_retry_of_task_id", table_name="service_request_tasks")
    op.drop_index("ix_service_request_tasks_status", table_name="service_request_tasks")
    op.drop_index("ix_service_request_tasks_service_type", table_name="service_request_tasks")
    op.drop_index("ix_service_request_tasks_request_id", table_name="service_request_tasks")
    op.drop_table("service_request_tasks")

    op.drop_index("ix_service_request_revisions_request_id", table_name="service_request_revisions")
    op.drop_table("service_request_revisions")

    op.drop_index("ix_service_request_drafts_request_id", table_name="service_request_drafts")
    op.drop_table("service_request_drafts")

    op.drop_index("ix_service_requests_assigned_consultant_id", table_name="service_requests")
    op.drop_index("ix_service_requests_status", table_name="service_requests")
    op.drop_index("ix_service_requests_service_type", table_name="service_requests")
    op.drop_index("ix_service_requests_user_id", table_name="service_requests")
    op.drop_table("service_requests")
