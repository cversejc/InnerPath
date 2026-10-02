import hashlib
import json
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.config import settings
from app.domains.reports.generation.mingli_foundation import calculate_mingli_foundation
from app.domains.reports.generation.report_prompt import SYSTEM_PROMPT, build_prompt
from app.domains.reports.generation.report_response_parser import (
    extract_chat_content,
    parse_ai_response,
)
from .definitions import (
    GLOBAL_POLICY,
    GLOBAL_POLICY_VERSION,
    validate_skill_specification,
)


@dataclass(frozen=True)
class ModelCompletion:
    content: str
    trace: dict[str, Any]


class ModelGateway(Protocol):
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model_policy: dict[str, Any],
    ) -> ModelCompletion: ...


class DeepSeekGateway:
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model_policy: dict[str, Any],
    ) -> ModelCompletion:
        model = model_policy.get("model") or settings.DEEPSEEK_MODEL
        timeout = min(max(float(model_policy.get("timeout_seconds") or 120), 1), 240)
        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": float(model_policy.get("temperature", 0.7)),
            "max_tokens": min(int(model_policy.get("max_tokens") or 8000), 16000),
            "stream": False,
            "thinking": {
                "type": "enabled" if settings.DEEPSEEK_THINKING else "disabled"
            },
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                settings.DEEPSEEK_API_URL,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                },
            )
            response.raise_for_status()
            response_data = response.json()
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        content = extract_chat_content(response_data)
        usage = response_data.get("usage") or {}
        choice = (response_data.get("choices") or [{}])[0]
        return ModelCompletion(
            content=content,
            trace={
                "provider": "deepseek",
                "model": model,
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "latency_ms": elapsed_ms,
                "estimated_cost": None,
                "finish_reason": choice.get("finish_reason"),
                "request_id": response_data.get("id"),
            },
        )


@dataclass(frozen=True)
class SkillExecutionResult:
    output_raw: str
    output_parsed: dict[str, Any]
    context_snapshot: dict[str, Any]
    model_trace: dict[str, Any]


class SkillExecutionError(ValueError):
    def __init__(self, code: str, model_trace: dict[str, Any] | None = None):
        super().__init__(code)
        self.model_trace = model_trace or {}


def _without_forbidden(value: Any, forbidden: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _without_forbidden(item, forbidden)
            for key, item in value.items()
            if str(key) not in forbidden
        }
    if isinstance(value, list):
        return [_without_forbidden(item, forbidden) for item in value]
    return deepcopy(value)


def build_context_envelope(
    input_data: dict[str, Any], specification: dict[str, Any]
) -> dict[str, Any]:
    source = deepcopy(input_data)
    nested = source.get("request_payload") or source.get("application_snapshot")
    if isinstance(nested, dict):
        source = {**nested, **source}
    profile = source.get("profile") or source.get("user_profile")
    if not isinstance(profile, dict):
        profile = {
            key: source.get(key)
            for key in (
                "name",
                "gender",
                "birth_year",
                "birth_month",
                "birth_day",
                "birth_hour",
                "birth_minute",
                "birth_is_leap_month",
                "calendar_type",
                "birth_time_precision",
                "birth_place",
                "mbti",
            )
            if source.get(key) is not None
        }
    profile = dict(profile)
    if "birth_time_precision" not in profile and profile.get("time_accuracy"):
        profile["birth_time_precision"] = profile["time_accuracy"]
    context = source.get("context")
    if not isinstance(context, dict):
        context = {
            "focus_topics": source.get("selected_topics", []),
            "additional_info": source.get("additional_info", ""),
        }
    context = dict(context)
    if "subject" not in context:
        context["subject"] = (
            context.get("current_challenge")
            or context.get("additional_info")
            or "人生说明书申请"
        )
    if "request" not in context:
        context["request"] = (
            context.get("expected_outcomes")
            or context.get("focus_topics")
            or ["自我探索"]
        )
    if "focus_topics" not in context and source.get("selected_topics"):
        context["focus_topics"] = source["selected_topics"]
    if "additional_info" not in context and source.get("additional_info"):
        context["additional_info"] = source["additional_info"]
    envelope = {
        "profile": profile,
        "context": context,
        "foundation_data": source.get("foundation_data"),
    }
    policy = specification["context_policy"]
    profile_fields = policy.get("profile_fields")
    if isinstance(profile_fields, list):
        envelope["profile"] = {
            key: value
            for key, value in envelope["profile"].items()
            if key in profile_fields
        }
    context_fields = policy.get("context_fields")
    if isinstance(context_fields, list):
        envelope["context"] = {
            key: value
            for key, value in envelope["context"].items()
            if key in context_fields
        }
    fields = policy.get("fields") or list(envelope)
    projection = policy.get("projection", "SELECT_FIELDS")
    if projection == "STRUCTURED_ONLY":
        fields = ["profile", "foundation_data"]
    elif projection == "SUMMARY":
        selected_profile = envelope["profile"]
        envelope["profile"] = {
            key: selected_profile.get(key)
            for key in ("name", "gender", "birth_year", "birth_month", "birth_day")
            if selected_profile.get(key) is not None
        }
        fields = ["profile", "context", "foundation_data"]
    elif projection == "FULL":
        envelope = source
        fields = list(envelope)
    else:
        fields = [field for field in fields if field in envelope]
    forbidden = set(policy.get("forbidden") or [])
    projected = {field: envelope[field] for field in fields if field in envelope}
    return _without_forbidden(projected, forbidden)


def _report_prompts(
    context: dict[str, Any],
    specification: dict[str, Any],
    runtime_instruction: str | None,
) -> tuple[str, str, dict[str, Any]]:
    profile = context.get("profile") or {}
    context_data = context.get("context") or {}
    foundation = context.get("foundation_data") or calculate_mingli_foundation(profile)
    report_input = {
        **profile,
        "selected_topics": context_data.get("focus_topics")
        or context_data.get("selected_topics")
        or [],
        "additional_info": context_data.get("additional_info") or "",
        "context": context_data,
        "foundation_data": foundation,
    }
    instructions = json.dumps(
        specification["instructions"], ensure_ascii=False, indent=2
    )
    runtime_note = (
        f"\n\n【本次运行补充要求】\n{runtime_instruction}"
        if runtime_instruction
        else ""
    )
    system_prompt = (
        f"{GLOBAL_POLICY}\n\n【产品生成规范】\n{SYSTEM_PROMPT}\n\n"
        f"【Skill Instructions】\n{instructions}{runtime_note}"
    )
    return system_prompt, build_prompt(report_input), foundation


def _authoring_prompts(
    context: dict[str, Any],
    specification: dict[str, Any],
    runtime_instruction: str | None,
) -> tuple[str, str]:
    processor = specification["processor_policy"]["processor"]
    objective = (
        "为咨询师生成 2 到 3 个叙事候选。候选中的 Finding 引用必须来自输入。"
        if processor == "reports.narrative_candidates"
        else "为指定章节生成一个有明确来源映射的报告片段。"
    )
    instructions = json.dumps(
        specification["instructions"], ensure_ascii=False, indent=2
    )
    runtime_note = (
        f"\n\n【本次运行补充要求】\n{runtime_instruction}"
        if runtime_instruction
        else ""
    )
    system_prompt = (
        f"{GLOBAL_POLICY}\n\n【任务】\n{objective}\n\n"
        f"【Skill Instructions】\n{instructions}{runtime_note}"
    )
    user_prompt = json.dumps(context, ensure_ascii=False, indent=2, default=str)
    return system_prompt, user_prompt


def _parse_json_output(raw: str) -> dict[str, Any]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            raise ValueError("skill_output_json_invalid")
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(candidate)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("skill_output_json_invalid") from error
    if not isinstance(parsed, dict):
        raise ValueError("skill_output_contract_invalid")
    return parsed


def _validate_authoring_output(
    output: dict[str, Any], context: dict[str, Any], processor: str
) -> None:
    context_data = context.get("context") or {}
    semantic_model = context_data.get("semantic_model") or {}
    finding_keys = {
        item.get("finding_key")
        for item in semantic_model.get("findings", [])
        if isinstance(item, dict) and item.get("finding_key")
    }
    if processor == "reports.narrative_candidates":
        candidates = output.get("candidates")
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= 3:
            raise ValueError("narrative_candidate_count_invalid")
        seen = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("narrative_candidate_invalid")
            candidate_key = candidate.get("candidate_key")
            if not isinstance(candidate_key, str) or not candidate_key.strip() or candidate_key in seen:
                raise ValueError("narrative_candidate_key_invalid")
            seen.add(candidate_key)
            for field in ("theme", "rationale"):
                if not isinstance(candidate.get(field), str) or not candidate[field].strip():
                    raise ValueError("narrative_candidate_invalid")
            for field in ("supporting_findings", "deemphasized_findings", "priority_blocks", "narrative_arc"):
                if not isinstance(candidate.get(field), list):
                    raise ValueError("narrative_candidate_invalid")
            references = set(candidate["supporting_findings"] + candidate["deemphasized_findings"])
            for block in candidate["priority_blocks"]:
                if isinstance(block, dict):
                    references.update(block.get("finding_refs") or [])
            if any(not isinstance(key, str) or key not in finding_keys for key in references):
                raise ValueError("narrative_candidate_unsupported_finding")
        return

    if output.get("status") not in {"READY_FOR_REVIEW", "MISSING_SEMANTIC_SUPPORT"}:
        raise ValueError("report_fragment_status_invalid")
    if output["status"] == "MISSING_SEMANTIC_SUPPORT":
        return
    for field in ("title", "content", "transition_hint"):
        if not isinstance(output.get(field), str):
            raise ValueError("report_fragment_output_invalid")
    if not output["title"].strip() or not output["content"].strip() or len(output["content"]) > 30000:
        raise ValueError("report_fragment_output_invalid")
    used_findings = output.get("used_findings")
    if (
        not isinstance(used_findings, list)
        or not used_findings
        or any(not isinstance(key, str) or key not in finding_keys for key in used_findings)
    ):
        raise ValueError("report_fragment_unsupported_finding")
    analysis_keys = {
        item.get("fragment_key")
        for item in semantic_model.get("analysis_fragments", [])
        if isinstance(item, dict) and item.get("fragment_key")
    }
    used_fragments = output.get("used_analysis_fragments")
    if (
        not isinstance(used_fragments, list)
        or any(not isinstance(key, str) or key not in analysis_keys for key in used_fragments)
    ):
        raise ValueError("report_fragment_unsupported_fragment")
    if not isinstance(output.get("used_actions"), list) or not isinstance(
        output.get("presentation_meta"), dict
    ):
        raise ValueError("report_fragment_output_invalid")


def _validate_output(
    output: dict[str, Any], raw: str, specification: dict[str, Any]
) -> None:
    contract = specification["output_contract"]
    if not isinstance(output, dict):
        raise ValueError("skill_output_contract_invalid")
    missing = [key for key in contract.get("required", []) if key not in output]
    if missing:
        raise ValueError("skill_output_contract_missing_fields")
    type_checks = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "number": lambda value: isinstance(value, (int, float))
        and not isinstance(value, bool),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
    }
    for key, schema in (contract.get("properties") or {}).items():
        expected = schema.get("type")
        if (
            key in output
            and expected in type_checks
            and not type_checks[expected](output[key])
        ):
            raise ValueError("skill_output_contract_type_invalid")
    blocked = specification["guardrails"].get("blocked_phrases") or []
    text = raw.casefold()
    if any(str(phrase).casefold() in text for phrase in blocked if phrase):
        raise ValueError("skill_guardrail_blocked")


async def execute_skill(
    *,
    skill_version: Any,
    input_data: dict[str, Any],
    runtime_instruction: str | None = None,
    gateway: ModelGateway | None = None,
) -> SkillExecutionResult:
    specification = validate_skill_specification(skill_version.specification_json)
    context = build_context_envelope(input_data, specification)
    if specification["identity"]["skill_key"] != skill_version.skill_key:
        raise ValueError("skill_identity_mismatch")
    processor = specification["processor_policy"]["processor"]
    if processor == "reports.single_step" and "reports.calculate_mingli_foundation" not in specification["tool_policy"].get("allowed", []):
        raise ValueError("skill_required_tool_not_allowed")
    if processor not in {"reports.single_step", "reports.narrative_candidates", "reports.fragment_authoring"}:
        raise ValueError("skill_processor_unsupported")
    profile = context.get("profile") or {}
    context_data = context.get("context") or {}
    missing_context = [
        field
        for field in specification["context_policy"].get("required", [])
        if context_data.get(field) in (None, "", [], {})
    ]
    if missing_context:
        raise ValueError("skill_context_contract_missing_fields")
    missing_input = [
        field
        for field in specification["input_contract"].get("required", [])
        if profile.get(field) in (None, "")
    ]
    if missing_input:
        raise ValueError("skill_input_contract_missing_fields")
    foundation = context.get("foundation_data")
    if processor == "reports.single_step":
        system_prompt, user_prompt, foundation = _report_prompts(
            context, specification, runtime_instruction
        )
    else:
        system_prompt, user_prompt = _authoring_prompts(
            context, specification, runtime_instruction
        )
    prompt_hash = hashlib.sha256(
        f"{system_prompt}\0{user_prompt}".encode("utf-8")
    ).hexdigest()
    provider = specification["model_policy"]["provider"]
    model = specification["model_policy"].get("model") or settings.DEEPSEEK_MODEL
    started = time.perf_counter()
    try:
        completion = await (gateway or DeepSeekGateway()).complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_policy=specification["model_policy"],
        )
    except Exception as error:
        trace = {
            "provider": provider,
            "model": model,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "prompt_sha256": prompt_hash,
            "output_validation": "not_run",
            "error_type": type(error).__name__,
        }
        raise SkillExecutionError("skill_model_gateway_failed", trace) from error
    trace = {
        **completion.trace,
        "skill_version_id": skill_version.id,
        "skill_key": skill_version.skill_key,
        "skill_version": skill_version.version,
        "processor": specification["processor_policy"]["processor"],
        "global_policy_version": GLOBAL_POLICY_VERSION,
        "prompt_sha256": prompt_hash,
        "output_validation": "passed",
    }
    try:
        output = (
            parse_ai_response(
                completion.content, {**profile, "foundation_data": foundation}
            )
            if processor == "reports.single_step"
            else _parse_json_output(completion.content)
        )
        _validate_output(output, completion.content, specification)
        if processor != "reports.single_step":
            _validate_authoring_output(output, context, processor)
    except Exception as error:
        trace["output_validation"] = "failed"
        trace["error_type"] = type(error).__name__
        code = (
            str(error) if isinstance(error, ValueError) else "skill_output_parse_failed"
        )
        raise SkillExecutionError(code, trace) from error
    return SkillExecutionResult(
        output_raw=completion.content,
        output_parsed=output,
        context_snapshot={**context, "foundation_data": foundation},
        model_trace=trace,
    )
