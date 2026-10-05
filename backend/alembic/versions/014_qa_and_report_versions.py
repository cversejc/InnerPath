"""Add final QA issues and immutable report delivery snapshots.

Revision ID: 014
Revises: 013
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_ref_id", sa.Integer(), nullable=True),
        sa.Column("issue_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="OPEN"),
        sa.Column("target_fragment_key", sa.String(length=200), nullable=True),
        sa.Column("target_fragment_revision_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "source_type IN ('PROGRAMMATIC', 'VALIDATOR')",
            name="ck_qa_issue_source_type",
        ),
        sa.CheckConstraint(
            "severity IN ('BLOCK', 'MAJOR', 'MINOR')", name="ck_qa_issue_severity"
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'ACCEPTED', 'DISMISSED')",
            name="ck_qa_issue_status",
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_ref_id"], ["skill_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_fragment_revision_id"],
            ["content_fragment_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_qa_issues_case_status_severity",
        "qa_issues",
        ["report_case_id", "status", "severity"],
    )
    op.create_index(
        "ix_qa_issues_case_source", "qa_issues", ["report_case_id", "source_type"]
    )
    op.create_index("ix_qa_issues_status", "qa_issues", ["status"])

    op.create_table(
        "report_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("workflow_version_id", sa.Integer(), nullable=False),
        sa.Column("narrative_plan_id", sa.Integer(), nullable=False),
        sa.Column("fragment_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("semantic_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("structured_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rendered_html", sa.Text(), nullable=False),
        sa.Column("pdf_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_version_id"], ["workflow_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["narrative_plan_id"], ["narrative_plans.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "report_case_id", "version_no", name="uq_report_version_case_version"
        ),
    )
    op.create_index("ix_report_versions_report_case_id", "report_versions", ["report_case_id"])
    op.execute(
        """
        CREATE FUNCTION prevent_report_version_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'report_version_immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_report_versions_immutable
        BEFORE UPDATE OR DELETE ON report_versions
        FOR EACH ROW EXECUTE FUNCTION prevent_report_version_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_report_versions_immutable ON report_versions")
    op.execute("DROP FUNCTION IF EXISTS prevent_report_version_mutation()")
    op.drop_index("ix_report_versions_report_case_id", table_name="report_versions")
    op.drop_table("report_versions")
    op.drop_index("ix_qa_issues_status", table_name="qa_issues")
    op.drop_index("ix_qa_issues_case_source", table_name="qa_issues")
    op.drop_index("ix_qa_issues_case_status_severity", table_name="qa_issues")
    op.drop_table("qa_issues")
