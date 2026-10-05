"""Add versioned, reviewed Dynamic Few-shot examples.

Revision ID: 015
Revises: 014
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_examples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_key", sa.String(length=100), nullable=False),
        sa.Column("target_fragment_key", sa.String(length=200), nullable=True),
        sa.Column("example_key", sa.String(length=64), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="CANDIDATE"),
        sa.Column("example_type", sa.String(length=24), nullable=False),
        sa.Column("scenario_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("applicability_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("teaching_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("anti_patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("source_case_id", sa.Integer(), nullable=True),
        sa.Column("source_skill_run_id", sa.Integer(), nullable=True),
        sa.Column("deidentified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("version_no > 0", name="ck_skill_example_version_positive"),
        sa.CheckConstraint(
            "status IN ('CANDIDATE', 'PUBLISHED', 'RETIRED')",
            name="ck_skill_example_status",
        ),
        sa.CheckConstraint(
            "example_type IN ('POSITIVE', 'CONTRASTIVE', 'MISSED_INSIGHT')",
            name="ck_skill_example_type",
        ),
        sa.CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)",
            name="ck_skill_example_quality_score",
        ),
        sa.ForeignKeyConstraint(
            ["source_case_id"], ["report_cases.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_skill_run_id"], ["skill_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "example_key", "version_no", name="uq_skill_example_key_version"
        ),
    )
    op.create_index("ix_skill_examples_skill_key", "skill_examples", ["skill_key"])
    op.create_index("ix_skill_examples_status", "skill_examples", ["status"])
    op.create_index(
        "ix_skill_examples_retrieval",
        "skill_examples",
        ["skill_key", "status", "target_fragment_key"],
    )
    op.create_index(
        "uq_skill_example_published_key",
        "skill_examples",
        ["example_key"],
        unique=True,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )
    op.execute(
        """
        CREATE FUNCTION prevent_published_skill_example_mutation() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.status = 'PUBLISHED' THEN
                    RAISE EXCEPTION 'skill_example_immutable';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.status = 'PUBLISHED' THEN
                IF NEW.status = 'RETIRED'
                   AND (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status') THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'skill_example_immutable';
            END IF;

            IF NEW.status = 'PUBLISHED'
               AND OLD.status = 'CANDIDATE'
               AND (to_jsonb(NEW) - ARRAY['status', 'reviewed_by', 'published_at'])
                   = (to_jsonb(OLD) - ARRAY['status', 'reviewed_by', 'published_at']) THEN
                RETURN NEW;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_skill_examples_immutable
        BEFORE UPDATE OR DELETE ON skill_examples
        FOR EACH ROW EXECUTE FUNCTION prevent_published_skill_example_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_skill_examples_immutable ON skill_examples")
    op.execute("DROP FUNCTION IF EXISTS prevent_published_skill_example_mutation()")
    op.drop_index("uq_skill_example_published_key", table_name="skill_examples")
    op.drop_index("ix_skill_examples_retrieval", table_name="skill_examples")
    op.drop_index("ix_skill_examples_status", table_name="skill_examples")
    op.drop_index("ix_skill_examples_skill_key", table_name="skill_examples")
    op.drop_table("skill_examples")
