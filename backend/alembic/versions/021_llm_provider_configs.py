"""Persist administrator-managed LLM provider profiles.

Revision ID: 021_llm_provider_configs
Revises: 020_merge_profile_routing
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa


revision = "021_llm_provider_configs"
down_revision = "020_merge_profile_routing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_provider_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="8000"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("thinking_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "provider IN ('deepseek', 'openai_compatible')",
            name="ck_llm_provider_configs_provider",
        ),
        sa.CheckConstraint(
            "temperature >= 0 AND temperature <= 2",
            name="ck_llm_provider_configs_temperature",
        ),
        sa.CheckConstraint(
            "max_tokens >= 1 AND max_tokens <= 32768",
            name="ck_llm_provider_configs_max_tokens",
        ),
        sa.CheckConstraint(
            "timeout_seconds >= 1 AND timeout_seconds <= 240",
            name="ck_llm_provider_configs_timeout",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("name", name="uq_llm_provider_configs_name"),
    )
    op.create_index(
        "ix_llm_provider_configs_is_default",
        "llm_provider_configs",
        ["is_default"],
    )
    op.create_index(
        "uq_llm_provider_configs_default",
        "llm_provider_configs",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
        sqlite_where=sa.text("is_default = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_llm_provider_configs_default", table_name="llm_provider_configs")
    op.drop_index("ix_llm_provider_configs_is_default", table_name="llm_provider_configs")
    op.drop_table("llm_provider_configs")
