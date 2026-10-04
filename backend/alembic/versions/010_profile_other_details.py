"""Store descriptions for optional profile choices.

Revision ID: 010
Revises: 009
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mingli_experience_other", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("default_usage_scenarios_other", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "default_usage_scenarios_other")
    op.drop_column("users", "mingli_experience_other")
