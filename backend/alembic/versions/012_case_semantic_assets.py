"""Add case evidence and versioned finding/content fragment assets.

Revision ID: 012
Revises: 011
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def _jsonb():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "case_evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("evidence_key", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=False),
        sa.Column("value_json", _jsonb(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("source_skill_run_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "source_type IN ('USER_PROVIDED', 'SYSTEM_CALCULATED', 'EXTERNAL_REFERENCE')",
            name="ck_case_evidence_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETRACTED')", name="ck_case_evidence_status"
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_skill_run_id"], ["skill_runs.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "report_case_id", "evidence_key", name="uq_case_evidence_key"
        ),
    )
    op.create_index(
        "ix_case_evidence_case_status",
        "case_evidence_items",
        ["report_case_id", "status"],
    )
    op.create_index("ix_case_evidence_items_status", "case_evidence_items", ["status"])

    op.create_table(
        "finding_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("finding_key", sa.String(length=200), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("semantic_revision", sa.Integer(), nullable=False),
        sa.Column("content_revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="FINDING"),
        sa.Column("semantic_role", sa.String(length=48), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=12), nullable=False),
        sa.Column("importance", sa.String(length=12), nullable=False),
        sa.Column("reportability", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PROPOSED"),
        sa.Column("evidence_refs", _jsonb(), nullable=False),
        sa.Column("relation_refs", _jsonb(), nullable=False),
        sa.Column("structured_data_json", _jsonb(), nullable=False),
        sa.Column("edit_kind", sa.String(length=12), nullable=False, server_default="SEMANTIC"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("owner_step_task_id", sa.Integer(), nullable=True),
        sa.Column("source_skill_run_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("revision_no > 0", name="ck_finding_revision_positive"),
        sa.CheckConstraint(
            "semantic_revision > 0 AND content_revision > 0",
            name="ck_finding_revision_counters_positive",
        ),
        sa.CheckConstraint(
            "kind IN ('FINDING', 'SIGNAL')", name="ck_finding_revision_kind"
        ),
        sa.CheckConstraint(
            "confidence IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_finding_revision_confidence",
        ),
        sa.CheckConstraint(
            "importance IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_finding_revision_importance",
        ),
        sa.CheckConstraint(
            "reportability IN ('INTERNAL_ONLY', 'OPTIONAL', 'RECOMMENDED', 'MUST_INCLUDE')",
            name="ck_finding_revision_reportability",
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'CONFIRMED', 'REJECTED', 'SUPERSEDED')",
            name="ck_finding_revision_status",
        ),
        sa.CheckConstraint(
            "edit_kind IN ('SEMANTIC', 'STYLE')", name="ck_finding_edit_kind"
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["owner_step_task_id"], ["step_tasks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_skill_run_id"], ["skill_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "report_case_id",
            "finding_key",
            "revision_no",
            name="uq_finding_revision_number",
        ),
    )
    op.create_index(
        "uq_finding_revision_current",
        "finding_revisions",
        ["report_case_id", "finding_key"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "ix_finding_revision_case_status",
        "finding_revisions",
        ["report_case_id", "status"],
    )
    op.create_index("ix_finding_revisions_is_current", "finding_revisions", ["is_current"])

    op.create_table(
        "content_fragment_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("fragment_key", sa.String(length=200), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("semantic_revision", sa.Integer(), nullable=False),
        sa.Column("content_revision", sa.Integer(), nullable=False),
        sa.Column("fragment_type", sa.String(length=16), nullable=False, server_default="ANALYSIS"),
        sa.Column("title", sa.String(length=240), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PROPOSED"),
        sa.Column("source_snapshot", _jsonb(), nullable=False),
        sa.Column("edit_kind", sa.String(length=12), nullable=False, server_default="SEMANTIC"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("owner_step_task_id", sa.Integer(), nullable=True),
        sa.Column("source_skill_run_id", sa.Integer(), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("revision_no > 0", name="ck_content_fragment_revision_positive"),
        sa.CheckConstraint(
            "semantic_revision > 0 AND content_revision > 0",
            name="ck_content_fragment_revision_counters_positive",
        ),
        sa.CheckConstraint(
            "fragment_type IN ('ANALYSIS', 'REPORT')",
            name="ck_content_fragment_type",
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'CONFIRMED', 'STALE')",
            name="ck_content_fragment_status",
        ),
        sa.CheckConstraint(
            "edit_kind IN ('SEMANTIC', 'STYLE')", name="ck_content_fragment_edit_kind"
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["owner_step_task_id"], ["step_tasks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_skill_run_id"], ["skill_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "report_case_id",
            "fragment_key",
            "revision_no",
            name="uq_content_fragment_revision_number",
        ),
    )
    op.create_index(
        "uq_content_fragment_revision_current",
        "content_fragment_revisions",
        ["report_case_id", "fragment_key"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "ix_content_fragment_case_status",
        "content_fragment_revisions",
        ["report_case_id", "status"],
    )
    op.create_index(
        "ix_content_fragment_revisions_is_current",
        "content_fragment_revisions",
        ["is_current"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_fragment_revisions_is_current",
        table_name="content_fragment_revisions",
    )
    op.drop_index(
        "ix_content_fragment_case_status", table_name="content_fragment_revisions"
    )
    op.drop_index(
        "uq_content_fragment_revision_current",
        table_name="content_fragment_revisions",
    )
    op.drop_table("content_fragment_revisions")

    op.drop_index("ix_finding_revisions_is_current", table_name="finding_revisions")
    op.drop_index("ix_finding_revision_case_status", table_name="finding_revisions")
    op.drop_index("uq_finding_revision_current", table_name="finding_revisions")
    op.drop_table("finding_revisions")

    op.drop_index("ix_case_evidence_items_status", table_name="case_evidence_items")
    op.drop_index("ix_case_evidence_case_status", table_name="case_evidence_items")
    op.drop_table("case_evidence_items")
