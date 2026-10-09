"""Join post-delivery service feedback with administrator LLM provider configs.

Revision ID: 022_merge_service_feedback_llm
Revises: 020_service_feedback, 021_llm_provider_configs
Create Date: 2026-10-08
"""


revision = "022_merge_service_feedback_llm"
down_revision = ("020_service_feedback", "021_llm_provider_configs")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
