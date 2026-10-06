"""Add ReportCase and sequential workflow persistence.

Revision ID: 010a
Revises: 010
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "010_report_workflow_foundation"
down_revision = "010_profile_other_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("service_request_id", sa.Integer(), nullable=True),
        sa.Column("source_report_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="CREATED"
        ),
        sa.Column(
            "application_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("application_submitted_at", sa.DateTime(), nullable=False),
        sa.Column("workflow_instance_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('CREATED', 'ACTIVE', 'BLOCKED', 'READY_TO_DELIVER', 'DELIVERED', 'CANCELLED')",
            name="ck_report_case_status",
        ),
        sa.CheckConstraint(
            "service_request_id IS NULL OR source_report_task_id IS NULL",
            name="ck_report_case_single_source",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["service_request_id"], ["service_requests.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_report_task_id"], ["report_tasks.task_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "service_request_id", name="uq_report_case_service_request"
        ),
        sa.UniqueConstraint("source_report_task_id", name="uq_report_case_report_task"),
    )
    op.create_index("ix_report_cases_status", "report_cases", ["status"])
    op.create_index(
        "ix_report_cases_user_status", "report_cases", ["user_id", "status"]
    )

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="DRAFT"
        ),
        sa.Column(
            "definition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("published_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("version > 0", name="ck_workflow_version_positive"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_workflow_version_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "workflow_key", "version", name="uq_workflow_version_key_version"
        ),
    )
    op.create_index(
        "ix_workflow_versions_workflow_key", "workflow_versions", ["workflow_key"]
    )
    op.create_index("ix_workflow_versions_status", "workflow_versions", ["status"])

    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("workflow_version_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="CREATED"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('CREATED', 'RUNNING', 'SUSPENDED', 'COMPLETED', 'CANCELLED')",
            name="ck_workflow_instance_status",
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_version_id"], ["workflow_versions.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_workflow_instances_report_case_id", "workflow_instances", ["report_case_id"]
    )
    op.create_index("ix_workflow_instances_status", "workflow_instances", ["status"])
    op.create_index(
        "ix_workflow_instances_case_status",
        "workflow_instances",
        ["report_case_id", "status"],
    )
    op.create_foreign_key(
        "fk_report_cases_workflow_instance",
        "report_cases",
        "workflow_instances",
        ["workflow_instance_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "step_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_instance_id", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("executor", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="PENDING"
        ),
        sa.Column("required_capability", sa.String(length=100), nullable=True),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("activation_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "executor IN ('HUMAN', 'AI', 'HYBRID')", name="ck_step_task_executor"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'READY', 'EXECUTING', 'WAITING_REVIEW', 'IN_REVIEW', 'NEEDS_REVISION', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_step_task_status",
        ),
        sa.CheckConstraint("sequence_no > 0", name="ck_step_task_sequence_positive"),
        sa.CheckConstraint(
            "activation_no >= 0", name="ck_step_task_activation_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_instance_id"], ["workflow_instances.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "workflow_instance_id", "step_key", name="uq_step_task_instance_key"
        ),
    )
    op.create_index(
        "ix_step_tasks_workflow_instance_id", "step_tasks", ["workflow_instance_id"]
    )
    op.create_index("ix_step_tasks_status", "step_tasks", ["status"])
    op.create_index(
        "ix_step_tasks_workflow_status",
        "step_tasks",
        ["workflow_instance_id", "status"],
    )

    op.create_table(
        "workflow_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="PENDING"
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PUBLISHED', 'FAILED')",
            name="ck_workflow_outbox_status",
        ),
    )
    op.create_index("ix_workflow_outbox_status", "workflow_outbox", ["status"])
    op.create_index(
        "ix_workflow_outbox_pending", "workflow_outbox", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_outbox_pending", table_name="workflow_outbox")
    op.drop_index("ix_workflow_outbox_status", table_name="workflow_outbox")
    op.drop_table("workflow_outbox")
    op.drop_index("ix_step_tasks_workflow_status", table_name="step_tasks")
    op.drop_index("ix_step_tasks_status", table_name="step_tasks")
    op.drop_index("ix_step_tasks_workflow_instance_id", table_name="step_tasks")
    op.drop_table("step_tasks")
    op.drop_constraint(
        "fk_report_cases_workflow_instance", "report_cases", type_="foreignkey"
    )
    op.drop_index("ix_workflow_instances_case_status", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_status", table_name="workflow_instances")
    op.drop_index(
        "ix_workflow_instances_report_case_id", table_name="workflow_instances"
    )
    op.drop_table("workflow_instances")
    op.drop_index("ix_workflow_versions_status", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_workflow_key", table_name="workflow_versions")
    op.drop_table("workflow_versions")
    op.drop_index("ix_report_cases_user_status", table_name="report_cases")
    op.drop_index("ix_report_cases_status", table_name="report_cases")
    op.drop_table("report_cases")
