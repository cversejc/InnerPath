"""Allow audited consultant corrections to calculated case evidence."""

from alembic import op


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("case_evidence_items") as batch_op:
        batch_op.drop_constraint("ck_case_evidence_source_type", type_="check")
        batch_op.create_check_constraint(
            "ck_case_evidence_source_type",
            "source_type IN ('USER_PROVIDED', 'SYSTEM_CALCULATED', 'CONSULTANT_CORRECTED', 'EXTERNAL_REFERENCE')",
        )


def downgrade() -> None:
    with op.batch_alter_table("case_evidence_items") as batch_op:
        batch_op.drop_constraint("ck_case_evidence_source_type", type_="check")
        batch_op.create_check_constraint(
            "ck_case_evidence_source_type",
            "source_type IN ('USER_PROVIDED', 'SYSTEM_CALCULATED', 'EXTERNAL_REFERENCE')",
        )
