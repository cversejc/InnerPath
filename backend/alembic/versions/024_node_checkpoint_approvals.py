"""Persist version-bound approvals for individual node review stages.

Revision ID: 024_node_checkpoints
Revises: 023_merge_review_feedback
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "024_node_checkpoints"
down_revision = "023_merge_review_feedback"
branch_labels = None
depends_on = None


def upgrade():
    document = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table(
        "node_checkpoint_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), sa.ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_task_id", sa.Integer(), sa.ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activation_no", sa.Integer(), nullable=False),
        sa.Column("checkpoint_key", sa.String(32), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("manifest_json", document, nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("report_case_id", "idempotency_key", name="uq_node_checkpoint_idempotency"),
        sa.UniqueConstraint("report_case_id", "step_task_id", "activation_no", "checkpoint_key", "fingerprint", name="uq_node_checkpoint_version"),
    )
    op.create_index("ix_node_checkpoint_approvals_report_case_id", "node_checkpoint_approvals", ["report_case_id"])


def downgrade():
    op.drop_index("ix_node_checkpoint_approvals_report_case_id", table_name="node_checkpoint_approvals")
    op.drop_table("node_checkpoint_approvals")
