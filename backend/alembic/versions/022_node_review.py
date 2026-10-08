"""Add whole-node review records without changing historical snapshots.

Revision ID: 022_node_review
Revises: 021_llm_provider_configs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "022_node_review"
down_revision = "021_llm_provider_configs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("report_cases", sa.Column("review_policy_version", sa.String(40), nullable=True))
    document = sa.JSON().with_variant(JSONB(), "postgresql")
    op.create_table("node_review_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), sa.ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_key", sa.String(8), nullable=False),
        sa.Column("metadata_json", document, nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("report_case_id", "step_key", name="uq_node_review_state"))
    op.create_table("node_review_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), sa.ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_task_id", sa.Integer(), sa.ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("activation_no", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("input_json", document, nullable=False),
        sa.Column("output_json", document),
        sa.Column("model_trace", document),
        sa.Column("error", sa.String(500)),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
        sa.UniqueConstraint("report_case_id", "idempotency_key", name="uq_node_review_command"))
    op.create_index("ix_node_review_commands_report_case_id", "node_review_commands", ["report_case_id"])
    op.create_table("node_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_case_id", sa.Integer(), sa.ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_task_id", sa.Integer(), sa.ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activation_no", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("check_command_id", sa.Integer(), sa.ForeignKey("node_review_commands.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("manifest_json", document, nullable=False),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("report_case_id", "step_task_id", "activation_no", "fingerprint", name="uq_node_approval_version"))


def downgrade():
    for name in ("node_approvals", "node_review_commands", "node_review_states"):
        op.drop_table(name)
    op.drop_column("report_cases", "review_policy_version")
