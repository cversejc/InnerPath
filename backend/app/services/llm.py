"""Provider-neutral chat interface for application and domain consumers."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import AsyncSessionLocal
from app.domains.llm.service import (
    RuntimeLLMConfig,
    resolve_runtime_config,
    runtime_config_from_environment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatCompletion:
    content: str
    provider: str
    model: str
    usage: dict[str, int | None]
    finish_reason: str | None
    latency_ms: int
    request_id: str | None
    thinking_enabled: bool


def _completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _message_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for part in value:
            if isinstance(part, str):
                parts.append(part)
            elif (
                isinstance(part, dict)
                and part.get("type") in {"text", "output_text"}
                and isinstance(part.get("text"), str)
            ):
                parts.append(part["text"])
        return "".join(parts)
    return ""


async def _resolve_config(configuration_id: int | None) -> RuntimeLLMConfig:
    try:
        async with AsyncSessionLocal() as db:
            return await resolve_runtime_config(db, configuration_id=configuration_id)
    except (SQLAlchemyError, RuntimeError, OSError):
        if configuration_id is not None:
            raise
        logger.warning("LLM configuration storage is unavailable; using environment fallback")
        return runtime_config_from_environment()


async def chat(
    messages: Sequence[dict[str, str]],
    *,
    configuration_id: int | None = None,
    configuration: RuntimeLLMConfig | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout_seconds: float | None = None,
    thinking: bool | None = None,
    allow_empty: bool = False,
    client_factory: Callable[..., Any] | None = None,
) -> ChatCompletion:
    """Send normalized chat messages through the selected provider adapter."""
    config = configuration or await _resolve_config(configuration_id)
    selected_model = model or config.model
    selected_temperature = config.temperature if temperature is None else temperature
    selected_thinking = config.thinking_enabled if thinking is None else thinking
    if max_tokens is None:
        selected_max_tokens = config.max_tokens
    else:
        token_limit = 32768 if selected_thinking else 16000
        selected_max_tokens = min(max_tokens, token_limit)
    selected_timeout = config.timeout_seconds if timeout_seconds is None else timeout_seconds

    body: dict[str, Any] = {
        "model": selected_model,
        "messages": list(messages),
        "temperature": selected_temperature,
        "max_tokens": selected_max_tokens,
        "stream": False,
    }
    if config.provider == "deepseek":
        body["thinking"] = {
            "type": "enabled" if selected_thinking else "disabled"
        }

    started = time.perf_counter()
    factory = client_factory or httpx.AsyncClient
    async with factory(timeout=selected_timeout) as client:
        response = await client.post(
            _completions_url(config.base_url),
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
        )
        response.raise_for_status()
        response_data = response.json()

    if not isinstance(response_data, dict):
        raise ValueError("llm_provider_response_invalid")
    choices = response_data.get("choices") or []
    choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    content = _message_content(message.get("content")) if isinstance(message, dict) else ""
    if not content and not allow_empty:
        raise ValueError("llm_provider_response_empty")

    raw_usage = response_data.get("usage") or {}
    if not isinstance(raw_usage, dict):
        raw_usage = {}
    usage = {
        "input_tokens": raw_usage.get("prompt_tokens"),
        "output_tokens": raw_usage.get("completion_tokens"),
        "total_tokens": raw_usage.get("total_tokens"),
    }
    return ChatCompletion(
        content=content,
        provider=config.provider,
        model=response_data.get("model") or selected_model,
        usage=usage,
        finish_reason=choice.get("finish_reason"),
        latency_ms=round((time.perf_counter() - started) * 1000),
        request_id=response_data.get("id"),
        thinking_enabled=selected_thinking if config.provider == "deepseek" else False,
    )
