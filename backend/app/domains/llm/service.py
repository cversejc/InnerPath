import base64
import hashlib
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.llm.models import LLMProviderConfig
from app.domains.llm.schemas import LLMConfigurationWrite


@dataclass(frozen=True)
class RuntimeLLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    thinking_enabled: bool
    configuration_id: int | None = None


def _cipher() -> Fernet:
    secret = settings.LLM_CONFIG_ENCRYPTION_KEY or settings.SECRET_KEY
    material = hashlib.sha256(
        b"innerseek-llm-provider-config\0" + secret.encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(material))


def encrypt_api_key(api_key: str) -> str:
    return _cipher().encrypt(api_key.encode("utf-8")).decode("ascii")


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _cipher().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as error:
        raise ValueError("llm_config_encryption_key_invalid") from error


def _row_api_key(row: LLMProviderConfig) -> str:
    if row.encrypted_api_key:
        return decrypt_api_key(row.encrypted_api_key)
    if row.provider == "deepseek":
        return settings.DEEPSEEK_API_KEY
    return ""


def runtime_config_from_row(row: LLMProviderConfig) -> RuntimeLLMConfig:
    api_key = _row_api_key(row)
    if not api_key:
        raise ValueError("llm_api_key_required")
    return RuntimeLLMConfig(
        provider=row.provider,
        base_url=row.base_url,
        model=row.model,
        api_key=api_key,
        temperature=row.temperature,
        max_tokens=row.max_tokens,
        timeout_seconds=row.timeout_seconds,
        thinking_enabled=row.thinking_enabled,
        configuration_id=row.id,
    )


def runtime_config_from_environment() -> RuntimeLLMConfig:
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("llm_provider_not_configured")
    return RuntimeLLMConfig(
        provider="deepseek",
        base_url=settings.DEEPSEEK_API_URL,
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        temperature=0.7,
        max_tokens=settings.DEEPSEEK_MAX_TOKENS,
        timeout_seconds=settings.DEEPSEEK_TIMEOUT_SECONDS,
        thinking_enabled=settings.DEEPSEEK_THINKING,
    )


def _payload_runtime_config(
    payload: LLMConfigurationWrite,
    *,
    existing: LLMProviderConfig | None = None,
) -> RuntimeLLMConfig:
    api_key = payload.api_key
    if not api_key and existing and existing.encrypted_api_key:
        api_key = decrypt_api_key(existing.encrypted_api_key)
    if not api_key and payload.provider == "deepseek":
        api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError("llm_api_key_required")
    return RuntimeLLMConfig(
        provider=payload.provider,
        base_url=payload.base_url,
        model=payload.model,
        api_key=api_key,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        timeout_seconds=payload.timeout_seconds,
        thinking_enabled=payload.thinking_enabled,
        configuration_id=existing.id if existing else None,
    )


def _api_key_source(row: LLMProviderConfig) -> str:
    if row.encrypted_api_key:
        return "saved"
    if row.provider == "deepseek" and settings.DEEPSEEK_API_KEY:
        return "environment"
    return "missing"


def configuration_response(row: LLMProviderConfig) -> dict:
    source = _api_key_source(row)
    return {
        "id": row.id,
        "name": row.name,
        "provider": row.provider,
        "base_url": row.base_url,
        "model": row.model,
        "temperature": row.temperature,
        "max_tokens": row.max_tokens,
        "timeout_seconds": row.timeout_seconds,
        "thinking_enabled": row.thinking_enabled,
        "is_default": row.is_default,
        "api_key_configured": source != "missing",
        "api_key_source": source,
    }


async def list_configurations(db: AsyncSession) -> list[LLMProviderConfig]:
    result = await db.scalars(
        select(LLMProviderConfig).order_by(
            LLMProviderConfig.is_default.desc(),
            LLMProviderConfig.updated_at.desc(),
            LLMProviderConfig.id.desc(),
        )
    )
    return list(result.all())


async def get_configuration(
    db: AsyncSession, configuration_id: int
) -> LLMProviderConfig:
    row = await db.get(LLMProviderConfig, configuration_id)
    if row is None:
        raise LookupError("llm_configuration_not_found")
    return row


async def save_configuration(
    db: AsyncSession,
    payload: LLMConfigurationWrite,
    *,
    actor_id: int,
    configuration_id: int | None = None,
) -> LLMProviderConfig:
    row = (
        await get_configuration(db, configuration_id)
        if configuration_id is not None
        else None
    )
    duplicate = await db.scalar(
        select(LLMProviderConfig.id).where(
            LLMProviderConfig.name == payload.name,
            LLMProviderConfig.id != (row.id if row else -1),
        )
    )
    if duplicate is not None:
        raise ValueError("llm_configuration_name_taken")

    current_default = await db.scalar(
        select(LLMProviderConfig.id).where(LLMProviderConfig.is_default.is_(True))
    )
    should_be_default = payload.is_default or (
        row is None and current_default is None and bool(payload.api_key)
    )
    has_fallback_key = bool(
        payload.api_key
        or (row and row.encrypted_api_key)
        or (payload.provider == "deepseek" and settings.DEEPSEEK_API_KEY)
    )
    if should_be_default and not has_fallback_key:
        raise ValueError("llm_api_key_required")

    if should_be_default:
        await db.execute(
            update(LLMProviderConfig).values(is_default=False)
        )

    if row is None:
        row = LLMProviderConfig(name=payload.name, created_by=actor_id)
        db.add(row)

    row.name = payload.name
    row.provider = payload.provider
    row.base_url = payload.base_url
    row.model = payload.model
    row.temperature = payload.temperature
    row.max_tokens = payload.max_tokens
    row.timeout_seconds = payload.timeout_seconds
    row.thinking_enabled = payload.thinking_enabled
    row.is_default = should_be_default
    row.updated_by = actor_id
    if payload.api_key:
        row.encrypted_api_key = encrypt_api_key(payload.api_key)
    await db.flush()
    return row


async def set_default_configuration(
    db: AsyncSession, configuration_id: int
) -> LLMProviderConfig:
    row = await get_configuration(db, configuration_id)
    runtime_config_from_row(row)
    await db.execute(update(LLMProviderConfig).values(is_default=False))
    row.is_default = True
    await db.flush()
    return row


async def delete_configuration(db: AsyncSession, configuration_id: int) -> str:
    row = await get_configuration(db, configuration_id)
    if row.is_default:
        raise ValueError("llm_default_configuration_cannot_be_deleted")
    name = row.name
    await db.delete(row)
    await db.flush()
    return name


async def resolve_runtime_config(
    db: AsyncSession,
    *,
    configuration_id: int | None = None,
    payload: LLMConfigurationWrite | None = None,
) -> RuntimeLLMConfig:
    if payload is not None:
        existing = (
            await get_configuration(db, configuration_id)
            if configuration_id is not None
            else None
        )
        return _payload_runtime_config(payload, existing=existing)

    if configuration_id is not None:
        return runtime_config_from_row(await get_configuration(db, configuration_id))

    active = await db.scalar(
        select(LLMProviderConfig).where(LLMProviderConfig.is_default.is_(True))
    )
    if active is not None:
        return runtime_config_from_row(active)
    return runtime_config_from_environment()


async def default_model_name(db: AsyncSession) -> str:
    scalar = getattr(db, "scalar", None)
    if not callable(scalar):
        return settings.DEEPSEEK_MODEL
    try:
        active = await scalar(
            select(LLMProviderConfig.model).where(
                LLMProviderConfig.is_default.is_(True)
            )
        )
    except (SQLAlchemyError, RuntimeError):
        return settings.DEEPSEEK_MODEL
    return active or settings.DEEPSEEK_MODEL


def environment_fallback_summary() -> dict[str, str | bool]:
    return {
        "provider": "deepseek",
        "base_url": settings.DEEPSEEK_API_URL,
        "model": settings.DEEPSEEK_MODEL,
        "configured": bool(settings.DEEPSEEK_API_KEY),
    }
