from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)

from app.db.base import Base, TimestampMixin


class LLMProviderConfig(Base, TimestampMixin):
    __tablename__ = "llm_provider_configs"
    __table_args__ = (
        UniqueConstraint("name", name="uq_llm_provider_configs_name"),
        CheckConstraint(
            "provider IN ('deepseek', 'openai_compatible')",
            name="ck_llm_provider_configs_provider",
        ),
        CheckConstraint(
            "temperature >= 0 AND temperature <= 2",
            name="ck_llm_provider_configs_temperature",
        ),
        CheckConstraint(
            "max_tokens >= 1 AND max_tokens <= 32768",
            name="ck_llm_provider_configs_max_tokens",
        ),
        CheckConstraint(
            "timeout_seconds >= 1 AND timeout_seconds <= 240",
            name="ck_llm_provider_configs_timeout",
        ),
        Index(
            "uq_llm_provider_configs_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default IS TRUE"),
            sqlite_where=text("is_default = 1"),
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    provider = Column(String(32), nullable=False)
    base_url = Column(String(500), nullable=False)
    model = Column(String(50), nullable=False)
    encrypted_api_key = Column(Text, nullable=True)
    temperature = Column(Float, nullable=False, default=0.7)
    max_tokens = Column(Integer, nullable=False, default=8000)
    timeout_seconds = Column(Integer, nullable=False, default=120)
    thinking_enabled = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
