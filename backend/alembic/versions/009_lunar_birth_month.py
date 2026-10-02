"""Preserve leap-month birth dates in user profiles.

Revision ID: 009
Revises: 008
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "birth_is_leap_month",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "birth_is_leap_month")
