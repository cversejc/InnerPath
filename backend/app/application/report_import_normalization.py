"""LLM normalization layer for the consultant report import fast path.

Import only accepts the three fixed sections the delivery assembler already
understands. Well-formed reports are parsed locally and never touch a model;
when the strict parser cannot recognize the structure, this module asks the
configured chat provider to reorganize the *same* text under the three
headings, then re-validates the answer with the same strict parser. The model
never becomes a source of content: the prompt forbids summarizing, rewriting
and inventing facts, and only a parseable answer is accepted.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from app.domains.content.report_import import (
    NORMALIZATION_PROMPT_VERSION,
    NORMALIZATION_SYSTEM_PROMPT,
    ImportedSection,
    ReportImportError,
    build_normalization_prompt,
    content_sha256,
    parse_report_content,
    render_import_markdown,
)
from app.services.llm import ChatCompletion, chat


logger = logging.getLogger(__name__)

NORMALIZATION_FAILED = "report_import_normalization_failed"

# Parse failures worth a model attempt: the text exists but its structure is
# unrecognized. Missing, oversized and hash-checked bodies fail earlier without
# spending a provider call.
RECOVERABLE_PARSE_CODES = frozenset(
    {
        "report_import_format_invalid",
        "report_import_sections_missing",
        "report_import_section_empty",
        "report_import_duplicate_section",
    }
)


@dataclass(frozen=True)
class PreparedReport:
    """The imported report plus the provenance the import run must persist."""

    sections: list[ImportedSection]
    content: str
    sha256: str
    used_model: bool
    prompt_sha256: Optional[str]
    trace: dict[str, Any]


class ReportNormalizationError(ReportImportError):
    """Stable `report_import_normalization_failed` code plus provider trace."""

    def __init__(
        self,
        *,
        trace: Optional[dict[str, Any]] = None,
        output_raw: Optional[str] = None,
    ):
        super().__init__(NORMALIZATION_FAILED)
        self.trace = trace or {}
        self.output_raw = output_raw


class NormalizationGateway(Protocol):
    async def complete(
        self, *, system_prompt: str, user_prompt: str
    ) -> ChatCompletion: ...


class ConfiguredNormalizationGateway:
    """Provider-neutral gateway backed by the configured chat provider."""

    async def complete(
        self, *, system_prompt: str, user_prompt: str
    ) -> ChatCompletion:
        return await chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            thinking=False,
            allow_empty=False,
            client_factory=httpx.AsyncClient,
        )


def prepare_local_report(sections: list[ImportedSection]) -> PreparedReport:
    """Build the prepared report for input the strict parser already accepts."""
    content = render_import_markdown(sections)
    return PreparedReport(
        sections=sections,
        content=content,
        sha256=content_sha256(content),
        used_model=False,
        prompt_sha256=None,
        trace={"used_model": False, "source": "local_parse"},
    )


def _completion_trace(completion: ChatCompletion) -> dict[str, Any]:
    return {
        "used_model": True,
        "provider": completion.provider,
        "model": completion.model,
        "input_tokens": completion.usage.get("input_tokens"),
        "output_tokens": completion.usage.get("output_tokens"),
        "total_tokens": completion.usage.get("total_tokens"),
        "latency_ms": completion.latency_ms,
        "finish_reason": completion.finish_reason,
        "request_id": completion.request_id,
        "thinking_enabled": completion.thinking_enabled,
        "prompt_version": NORMALIZATION_PROMPT_VERSION,
    }


async def normalize_report_content(
    content: str,
    *,
    parse_error: ReportImportError,
    gateway: Optional[NormalizationGateway] = None,
) -> PreparedReport:
    """Reorganize arbitrary report text into the three required sections.

    Any provider error, empty answer or still-unparseable answer surfaces as
    `report_import_normalization_failed` so the HTTP layer returns one stable
    422 instead of leaking provider details.
    """
    system_prompt = NORMALIZATION_SYSTEM_PROMPT
    user_prompt = build_normalization_prompt(content)
    prompt_sha256 = hashlib.sha256(
        f"{system_prompt}\n\n{user_prompt}".encode("utf-8")
    ).hexdigest()
    base_trace = {
        "used_model": True,
        "prompt_sha256": prompt_sha256,
        "prompt_version": NORMALIZATION_PROMPT_VERSION,
        "trigger_parse_error": str(parse_error),
    }
    provider = gateway or ConfiguredNormalizationGateway()
    try:
        completion = await provider.complete(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
    except ReportNormalizationError:
        raise
    except Exception as error:  # provider, transport and configuration failures
        logger.warning(
            "report import normalization call failed: %s", type(error).__name__
        )
        raise ReportNormalizationError(
            trace={
                **base_trace,
                "output_validation": "skipped",
                "error_type": type(error).__name__,
                "error": str(error)[:500],
            }
        ) from error

    trace = {**base_trace, **_completion_trace(completion)}
    raw = completion.content if isinstance(completion.content, str) else ""
    raw = raw.strip()
    if not raw:
        logger.warning("report import normalization returned empty content")
        raise ReportNormalizationError(
            trace={**trace, "output_validation": "failed", "parse_error": "empty"},
            output_raw=raw or None,
        )
    try:
        sections = parse_report_content(raw)
    except ReportImportError as error:
        logger.warning("report import normalization output rejected: %s", error)
        raise ReportNormalizationError(
            trace={
                **trace,
                "output_validation": "failed",
                "parse_error": str(error),
            },
            output_raw=raw,
        ) from error

    canonical = render_import_markdown(sections)
    return PreparedReport(
        sections=sections,
        content=canonical,
        sha256=content_sha256(canonical),
        used_model=True,
        prompt_sha256=prompt_sha256,
        trace={**trace, "output_validation": "passed"},
    )
