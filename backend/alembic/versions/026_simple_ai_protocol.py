"""Add execution, revision and review state for the AI-assisted Simple protocol.

Revision ID: 026_simple_ai_protocol
Revises: 025_merge_simple_review
Create Date: 2026-10-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "026_simple_ai_protocol"
down_revision: Union[str, Sequence[str], None] = "025_merge_simple_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    document = sa.JSON().with_variant(JSONB(), "postgresql")

    op.create_table(
        "simple_step_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "report_case_id",
            sa.Integer(),
            sa.ForeignKey("report_cases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "step_task_id",
            sa.Integer(),
            sa.ForeignKey("step_tasks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column(
            "execution_status",
            sa.String(length=24),
            nullable=False,
            server_default="READY",
        ),
        sa.Column(
            "dependency_status",
            sa.String(length=16),
            nullable=False,
            server_default="CURRENT",
        ),
        sa.Column("activation_no", sa.Integer(), nullable=False),
        sa.Column("current_revision_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_revision_id", sa.Integer(), nullable=True),
        sa.Column(
            "active_skill_run_id",
            sa.Integer(),
            sa.ForeignKey("skill_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("input_snapshot", document, nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "execution_status IN "
            "('READY', 'GENERATING', 'IN_REVIEW', 'REVISING', 'FAILED', 'COMPLETED')",
            name="ck_simple_step_execution_status",
        ),
        sa.CheckConstraint(
            "dependency_status IN ('CURRENT', 'STALE')",
            name="ck_simple_step_execution_dependency_status",
        ),
        sa.CheckConstraint(
            "activation_no >= 1",
            name="ck_simple_step_execution_activation_positive",
        ),
        sa.UniqueConstraint(
            "report_case_id",
            "step_key",
            name="uq_simple_step_execution_case_step",
        ),
    )
    op.create_index(
        "ix_simple_step_executions_report_case_id",
        "simple_step_executions",
        ["report_case_id"],
    )
    op.create_index(
        "ix_simple_step_executions_execution_status",
        "simple_step_executions",
        ["execution_status"],
    )
    op.create_index(
        "ix_simple_step_executions_dependency_status",
        "simple_step_executions",
        ["dependency_status"],
    )
    op.create_index(
        "ix_simple_step_executions_case_status",
        "simple_step_executions",
        ["report_case_id", "execution_status"],
    )

    op.create_table(
        "simple_step_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Integer(),
            sa.ForeignKey("simple_step_executions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("revision_type", sa.String(length=24), nullable=False),
        sa.Column(
            "parent_revision_id",
            sa.Integer(),
            sa.ForeignKey("simple_step_revisions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_content", document, nullable=True),
        sa.Column("source_revision_refs", document, nullable=False),
        sa.Column(
            "skill_run_id",
            sa.Integer(),
            sa.ForeignKey("skill_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "revision_type IN "
            "('INITIAL', 'AI_REVISION', 'REGENERATE', 'MANUAL_EDIT')",
            name="ck_simple_step_revision_type",
        ),
        sa.CheckConstraint(
            "revision_no > 0",
            name="ck_simple_step_revision_positive",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "revision_no",
            name="uq_simple_step_revision_execution_no",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_simple_step_revision_idempotency",
        ),
    )
    op.create_index(
        "ix_simple_step_revisions_execution_id",
        "simple_step_revisions",
        ["execution_id"],
    )
    op.create_index(
        "ix_simple_step_revisions_execution_created",
        "simple_step_revisions",
        ["execution_id", "created_at"],
    )

    op.create_table(
        "simple_review_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Integer(),
            sa.ForeignKey("simple_step_executions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_revision_id",
            sa.Integer(),
            sa.ForeignKey("simple_step_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "review_mode",
            sa.String(length=16),
            nullable=False,
            server_default="OWNER",
        ),
        sa.Column(
            "operator_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "on_behalf_of_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "decision IN "
            "('APPROVE', 'REQUEST_REVISION', 'REGENERATE', 'MANUAL_EDIT', 'REOPEN')",
            name="ck_simple_review_decision",
        ),
        sa.CheckConstraint(
            "review_mode IN ('OWNER', 'ADMIN', 'DELEGATED')",
            name="ck_simple_review_decision_review_mode",
        ),
        sa.CheckConstraint(
            "(review_mode = 'OWNER' AND on_behalf_of_user_id IS NULL) "
            "OR (review_mode <> 'OWNER' AND on_behalf_of_user_id IS NOT NULL)",
            name="ck_simple_review_decision_delegation_identity",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_simple_review_decision_idempotency",
        ),
    )
    op.create_index(
        "ix_simple_review_decisions_execution_id",
        "simple_review_decisions",
        ["execution_id"],
    )
    op.create_index(
        "ix_simple_review_decisions_execution_created",
        "simple_review_decisions",
        ["execution_id", "created_at"],
    )

    # SQLite test fixtures only need the schema; ORM events cover immutability
    # there.  PostgreSQL is the responsibility environment and gets real
    # database-level triggers.
    if _is_postgresql():
        op.execute(
            """
            CREATE FUNCTION prevent_simple_ai_record_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'simple_ai_record_immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_simple_step_revisions_immutable
            BEFORE UPDATE OR DELETE ON simple_step_revisions
            FOR EACH ROW EXECUTE FUNCTION prevent_simple_ai_record_mutation()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_simple_review_decisions_immutable
            BEFORE UPDATE OR DELETE ON simple_review_decisions
            FOR EACH ROW EXECUTE FUNCTION prevent_simple_ai_record_mutation()
            """
        )


def downgrade() -> None:
    if _is_postgresql():
        op.execute(
            "DROP TRIGGER IF EXISTS trg_simple_review_decisions_immutable "
            "ON simple_review_decisions"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_simple_step_revisions_immutable "
            "ON simple_step_revisions"
        )
        op.execute("DROP FUNCTION IF EXISTS prevent_simple_ai_record_mutation()")

    op.drop_index(
        "ix_simple_review_decisions_execution_created",
        table_name="simple_review_decisions",
    )
    op.drop_index(
        "ix_simple_review_decisions_execution_id",
        table_name="simple_review_decisions",
    )
    op.drop_table("simple_review_decisions")

    op.drop_index(
        "ix_simple_step_revisions_execution_created",
        table_name="simple_step_revisions",
    )
    op.drop_index(
        "ix_simple_step_revisions_execution_id",
        table_name="simple_step_revisions",
    )
    op.drop_table("simple_step_revisions")

    op.drop_index(
        "ix_simple_step_executions_case_status",
        table_name="simple_step_executions",
    )
    op.drop_index(
        "ix_simple_step_executions_dependency_status",
        table_name="simple_step_executions",
    )
    op.drop_index(
        "ix_simple_step_executions_execution_status",
        table_name="simple_step_executions",
    )
    op.drop_index(
        "ix_simple_step_executions_report_case_id",
        table_name="simple_step_executions",
    )
    op.drop_table("simple_step_executions")
