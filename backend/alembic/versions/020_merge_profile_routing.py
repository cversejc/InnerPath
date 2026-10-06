"""Join the legacy profile-details revision with consultant specialty routing.

Revision ID: 020_merge_profile_routing
Revises: 019, 019_consultant_specialty_routing
Create Date: 2026-10-06
"""


revision = "020_merge_profile_routing"
down_revision = ("019", "019_consultant_specialty_routing")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
