"""Add versioned AI skills and skill run tracing.

Revision ID: 011
Revises: 010
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_skill_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="DRAFT"
        ),
        sa.Column(
            "specification_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("published_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("version > 0", name="ck_ai_skill_version_positive"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'EVALUATION', 'PUBLISHED', 'RETIRED')",
            name="ck_ai_skill_version_status",
        ),
        sa.CheckConstraint(
            "category IN ('ANALYSIS', 'ACTION', 'AUTHORING', 'VALIDATOR')",
            name="ck_ai_skill_version_category",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "skill_key", "version", name="uq_ai_skill_version_key_version"
        ),
    )
    op.create_index(
        "ix_ai_skill_versions_skill_key", "ai_skill_versions", ["skill_key"]
    )
    op.create_index("ix_ai_skill_versions_status", "ai_skill_versions", ["status"])

    op.create_table(
        "skill_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_version_id", sa.Integer(), nullable=False),
        sa.Column("report_case_id", sa.Integer(), nullable=True),
        sa.Column("workflow_instance_id", sa.Integer(), nullable=True),
        sa.Column("step_task_id", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_key", sa.String(length=128), nullable=True),
        sa.Column("run_type", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="PENDING"
        ),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("runtime_instruction", sa.Text(), nullable=True),
        sa.Column(
            "input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("output_raw", sa.Text(), nullable=True),
        sa.Column(
            "output_parsed", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "selected_examples", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "selected_knowledge",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "model_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "run_type IN ('INITIAL', 'REGENERATE', 'REWRITE', 'VALIDATE', 'EVALUATION')",
            name="ck_skill_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_skill_run_status",
        ),
        sa.ForeignKeyConstraint(
            ["skill_version_id"], ["ai_skill_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_instance_id"], ["workflow_instances.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["step_task_id"], ["step_tasks.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_skill_run_idempotency_key"),
    )
    op.create_index(
        "ix_skill_runs_skill_version_id", "skill_runs", ["skill_version_id"]
    )
    op.create_index("ix_skill_runs_status", "skill_runs", ["status"])
    op.create_index(
        "ix_skill_runs_case_status", "skill_runs", ["report_case_id", "status"]
    )
    op.create_index(
        "ix_skill_runs_version_created",
        "skill_runs",
        ["skill_version_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_skill_runs_version_created", table_name="skill_runs")
    op.drop_index("ix_skill_runs_case_status", table_name="skill_runs")
    op.drop_index("ix_skill_runs_status", table_name="skill_runs")
    op.drop_index("ix_skill_runs_skill_version_id", table_name="skill_runs")
    op.drop_table("skill_runs")
    op.drop_index("ix_ai_skill_versions_status", table_name="ai_skill_versions")
    op.drop_index("ix_ai_skill_versions_skill_key", table_name="ai_skill_versions")
    op.drop_table("ai_skill_versions")
