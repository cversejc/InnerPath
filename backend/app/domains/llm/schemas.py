from typing import Literal
from urllib.parse import urlsplit

from pydantic import ConfigDict, Field, field_validator
from app.core.schemas import APIModel as BaseModel


ProviderName = Literal["deepseek", "openai_compatible"]


class LLMConfigurationWrite(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    provider: ProviderName
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=50)
    api_key: str | None = Field(default=None, max_length=8192)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=8000, ge=1, le=32768)
    timeout_seconds: int = Field(default=120, ge=1, le=240)
    thinking_enabled: bool = False
    is_default: bool = False

    @field_validator("name", "model")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value_required")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("base_url_must_be_http_url")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("base_url_must_not_contain_credentials_or_query")
        return value

    @field_validator("api_key")
    @classmethod
    def trim_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class LLMConfigurationTest(LLMConfigurationWrite):
    configuration_id: int | None = Field(default=None, ge=1)


class LLMConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider: ProviderName
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    thinking_enabled: bool
    is_default: bool
    api_key_configured: bool
    api_key_source: Literal["saved", "environment", "missing"]


class LLMConfigurationListResponse(BaseModel):
    items: list[LLMConfigurationResponse]
    environment_fallback: dict[str, str | bool]


class LLMTestResponse(BaseModel):
    success: bool = True
    provider: ProviderName
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
