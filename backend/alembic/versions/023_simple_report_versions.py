"""Add immutable full-text versions for the simplified report workflow.

Revision ID: 023_simple_report_versions
Revises: 022_merge_service_feedback_llm
Create Date: 2026-10-08
"""

from alembic import op
import sqlalchemy as sa


revision = "023_simple_report_versions"
down_revision = "022_merge_service_feedback_llm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simple_report_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("step_task_id", sa.Integer(), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=20), nullable=False),
        sa.Column("source_step_key", sa.String(length=100), nullable=False),
        sa.Column("report_text", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "is_final", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["step_task_id"], ["step_tasks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "report_case_id",
            "version_no",
            name="uq_simple_report_version_case_version",
        ),
    )
    op.create_index(
        "ix_simple_report_versions_report_case_id",
        "simple_report_versions",
        ["report_case_id"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_simple_report_version_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'simple_report_version_immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_simple_report_versions_immutable
        BEFORE UPDATE OR DELETE ON simple_report_versions
        FOR EACH ROW EXECUTE FUNCTION prevent_simple_report_version_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_simple_report_versions_immutable "
        "ON simple_report_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_simple_report_version_mutation()")
    op.drop_index(
        "ix_simple_report_versions_report_case_id",
        table_name="simple_report_versions",
    )
    op.drop_table("simple_report_versions")
