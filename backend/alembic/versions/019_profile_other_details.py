"""Bridge the earlier local profile-details revision after the chain is normalized.

Revision ID: 019
Revises: 018
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "mingli_experience_other" not in columns:
        op.add_column(
            "users",
            sa.Column("mingli_experience_other", sa.Text(), nullable=True),
        )
    if "default_usage_scenarios_other" not in columns:
        op.add_column(
            "users",
            sa.Column("default_usage_scenarios_other", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    pass
