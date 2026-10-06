"""Add versioned narrative plans and report fragment provenance.

Revision ID: 013
Revises: 012
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "narrative_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PROPOSED"),
        sa.Column("selected_skill_run_id", sa.Integer(), nullable=False),
        sa.Column("selected_candidate_key", sa.String(length=100), nullable=False),
        sa.Column("plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("version_no > 0", name="ck_narrative_plan_version_positive"),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'CONFIRMED', 'STALE', 'SUPERSEDED')",
            name="ck_narrative_plan_status",
        ),
        sa.ForeignKeyConstraint(
            ["report_case_id"], ["report_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["selected_skill_run_id"], ["skill_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "report_case_id", "version_no", name="uq_narrative_plan_case_version"
        ),
    )
    op.create_index(
        "uq_narrative_plan_current",
        "narrative_plans",
        ["report_case_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "ix_narrative_plan_case_status",
        "narrative_plans",
        ["report_case_id", "status"],
    )
    op.create_index(
        "ix_narrative_plan_skill_run",
        "narrative_plans",
        ["selected_skill_run_id"],
    )
    op.add_column(
        "content_fragment_revisions",
        sa.Column("source_narrative_plan_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_content_fragment_narrative_plan",
        "content_fragment_revisions",
        "narrative_plans",
        ["source_narrative_plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_content_fragment_narrative_plan",
        "content_fragment_revisions",
        ["source_narrative_plan_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_fragment_narrative_plan",
        table_name="content_fragment_revisions",
    )
    op.drop_constraint(
        "fk_content_fragment_narrative_plan",
        "content_fragment_revisions",
        type_="foreignkey",
    )
    op.drop_column("content_fragment_revisions", "source_narrative_plan_id")
    op.drop_index("ix_narrative_plan_skill_run", table_name="narrative_plans")
    op.drop_index("ix_narrative_plan_case_status", table_name="narrative_plans")
    op.drop_index("uq_narrative_plan_current", table_name="narrative_plans")
    op.drop_table("narrative_plans")
