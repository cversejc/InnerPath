"""Add user-owned daily action and decision logs.

Revision ID: 003
Revises: 002
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "decision_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="action"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="done"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_logs_user_id", "decision_logs", ["user_id"], unique=False)
    op.create_index("ix_decision_logs_log_date", "decision_logs", ["log_date"], unique=False)


def downgrade():
    op.drop_index("ix_decision_logs_log_date", table_name="decision_logs")
    op.drop_index("ix_decision_logs_user_id", table_name="decision_logs")
    op.drop_table("decision_logs")
