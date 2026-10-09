"""merge simplified report and node review revisions

Revision ID: 025_merge_simple_review
Revises: 023_simple_report_versions, 024_node_checkpoints
Create Date: 2026-10-09
"""

from typing import Sequence, Union

revision: str = "025_merge_simple_review"
down_revision: Union[str, Sequence[str], None] = (
    "023_simple_report_versions",
    "024_node_checkpoints",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
