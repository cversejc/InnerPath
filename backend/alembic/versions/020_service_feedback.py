"""Add optional post-delivery user service feedback."""

from alembic import op
import sqlalchemy as sa


revision = "020_service_feedback"
down_revision = "019_consultant_specialty_routing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("service_request_id", sa.Integer(), nullable=True),
        sa.Column("calendar_request_id", sa.Integer(), nullable=True),
        sa.Column("feedback_type", sa.String(length=20), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NEW"),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(service_request_id IS NOT NULL AND calendar_request_id IS NULL) "
            "OR (service_request_id IS NULL AND calendar_request_id IS NOT NULL)",
            name="ck_service_feedback_one_target",
        ),
        sa.CheckConstraint(
            "feedback_type IN ('PRAISE', 'SUGGESTION', 'COMPLAINT')",
            name="ck_service_feedback_type",
        ),
        sa.CheckConstraint(
            "status IN ('NEW', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_service_feedback_status",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_service_feedback_rating",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_request_id"], ["service_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["calendar_request_id"], ["calendar_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("service_request_id", name="uq_service_feedback_request"),
        sa.UniqueConstraint("calendar_request_id", name="uq_service_feedback_calendar"),
    )
    op.create_index(
        "ix_service_feedback_status_created",
        "service_feedback",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_service_feedback_user_created",
        "service_feedback",
        ["user_id", "created_at"],
    )
    op.create_index("ix_service_feedback_status", "service_feedback", ["status"])


def downgrade() -> None:
    op.drop_index("ix_service_feedback_status", table_name="service_feedback")
    op.drop_index("ix_service_feedback_user_created", table_name="service_feedback")
    op.drop_index("ix_service_feedback_status_created", table_name="service_feedback")
    op.drop_table("service_feedback")
