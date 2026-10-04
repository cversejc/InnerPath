import hashlib
import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.config import settings
from app.domains.quality.scorecard import validate_scorecard
from app.domains.content.framework_coverage import (
    normalize_coverage, normalize_requirement_coverage, normalize_framework_review,
)
from app.domains.content.action_contract import validate_growth_experiments
from app.domains.content.reasoning_contract import (
    ANALYSIS_STRUCTURES, normalize_structured_analysis, validate_action_reasoning,
    validate_reasoning_contract,
    validate_timeline_source,
    validate_priority_blocks,
    RESOURCE_ROLES,
)
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
    projected = _without_forbidden(projected, forbidden)
    knowledge = specification.get("knowledge_policy", {}).get("snapshot") or []
    if knowledge:
        projected["skill_knowledge"] = deepcopy(knowledge)
    example_policy = specification.get("example_policy") or {}
    examples = source.get("few_shot_examples")
    if example_policy.get("enabled") and isinstance(examples, list):
        projected["few_shot_examples"] = deepcopy(examples[:3])
    return projected


def _example_guidance(examples: list[dict[str, Any]]) -> str:
    if not examples:
        return ""
    example_data = json.dumps(examples, ensure_ascii=False, indent=2, default=str)
    return (
        "\n\n【已审核的脱敏示例】\n"
        "示例只用于参考结构、风格和专业表达。不得复制示例中的人物事实、结论或情境，"
        "不得把示例当作当前用户的证据。\n"
        f"{example_data}"
    )


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
        f"{_example_guidance(context.get('few_shot_examples') or [])}"
    )
    return system_prompt, build_prompt(report_input), foundation


def _authoring_prompts(
    context: dict[str, Any],
    specification: dict[str, Any],
    runtime_instruction: str | None,
) -> tuple[str, str]:
    processor = specification["processor_policy"]["processor"]
    objectives = {
        "reports.narrative_candidates": "为咨询师生成 2 到 3 个叙事候选。候选中的 Finding 引用必须来自输入。",
        "reports.fragment_authoring": "为指定章节生成一个有明确来源映射的报告片段。",
        "reports.validator": "审核最终报告中的事实忠实度、语义一致性、安全、叙事、行动和个性化，只输出可以定位和修复的问题。",
    }
    objective = objectives[processor]
    instructions = json.dumps(
        specification["instructions"], ensure_ascii=False, indent=2
    )
    output_contract = json.dumps(
        specification["output_contract"], ensure_ascii=False, indent=2
    )
    candidate_note = ""
    semantics = (context.get("context") or {}).get("semantic_model") or {}
    if processor == "reports.narrative_candidates" and semantics.get("reasoning_contract"):
        addressed = {k for f in semantics.get("findings", []) if f.get("semantic_role") == "ACTION"
                     for k in (f.get("structured_data") or {}).get("block_refs", [])}
        core_blocks = [{"finding_key": f["finding_key"], "claim": f["claim"]}
                       for f in semantics.get("findings", []) if f.get("semantic_role") == "BLOCK" and f["finding_key"] in addressed]
        candidate_note = (
            "\n【卡点选择契约】priority_blocks是具体卡点，不是三章目录、资源、能力或动作。"
            f"本案例有{len(core_blocks)}个有行动承接的BLOCK，每个候选都使用这些BLOCK，改变排列和叙事重点即可。"
            "每个对象finding_refs只放一个以下BLOCK的ID，不添加其他ID；旁证放supporting_findings。"
            "不要为4–5项凑数：只有3个真实BLOCK就返回3个。三章阅读顺序放在narrative_arc。\n"
            f"{json.dumps(core_blocks, ensure_ascii=False)}\n"
            "每个候选的priority_blocks严格采用这个结构，仅修改title为适合主线的读者语言，必要时调整顺序：\n"
            f"{json.dumps([{'title': '用读者语言写此卡点', 'finding_refs': [b['finding_key']]} for b in core_blocks[:5]], ensure_ascii=False)}\n"
        )
    qa_input = (context.get("context") or {}).get("qa_input") or {}
    if processor == "reports.validator" and qa_input.get("scorecard_required"):
        candidate_note += (
            "\n【本次必填评分结构】输出顶层必须有scorecard，不能改名为scores、quality_assessment或total_score。"
            "scorecard.dimensions必须含以下全部维度；每项为{score:整数, reason:理由, fragment_keys:正文片段ID数组}。"
            "score不得超出该维度满分，总分由程序计算，不要只返回总分。按真实质量评分，不填默认满分。\n"
            f"{json.dumps(qa_input.get('scoring_rubric') or {}, ensure_ascii=False)}\n"
        )
    runtime_note = (
        f"\n\n【本次运行补充要求】\n{runtime_instruction}"
        if runtime_instruction
        else ""
    )
    system_prompt = (
        f"{GLOBAL_POLICY}\n\n【任务】\n{objective}\n\n"
        "只输出符合契约的严格 JSON，不附加 Markdown、推理过程或解释文字。\n\n"
        "【机器可读输出契约】\n必须返回所有 required 字段，并按 properties 的类型输出；"
        "不要改名或省略字段。\n"
        f"{output_contract}\n\n"
        f"【Skill Instructions】\n{instructions}{candidate_note}{runtime_note}"
        f"{_example_guidance(context.get('few_shot_examples') or [])}"
    )
    user_prompt = json.dumps(context, ensure_ascii=False, indent=2, default=str)
    return system_prompt, user_prompt


def _analysis_prompts(
    context: dict[str, Any],
    specification: dict[str, Any],
    runtime_instruction: str | None,
) -> tuple[str, str]:
    instructions = json.dumps(
        specification["instructions"], ensure_ascii=False, indent=2
    )
    output_contract = json.dumps(
        specification["output_contract"], ensure_ascii=False, indent=2
    )
    runtime_note = (
        f"\n\n【本次运行补充要求】\n{runtime_instruction}"
        if runtime_instruction
        else ""
    )
    analysis_context = context.get("analysis_context") or {}
    structure_note = ""
    if analysis_context.get("reasoning_contract"):
        validate_reasoning_contract(analysis_context["reasoning_contract"])
        stage_prefix = f"analysis.{str(analysis_context.get('step_key', '')).lower()}."
        required_structures = {key: fields for key, fields in ANALYSIS_STRUCTURES.items() if key.startswith(stage_prefix)}
        structure_note = (
            "\n【本阶段强制的结构化产物】\n"
            "以下fragment_key各对象必须有structured_analysis，不能只放framework_coverage。"
            "structured_analysis的必填字段是status、reason、quote、follow_up_questions、details；"
            "FULFILLED的details必须且只能使用对应表的所有英文键，值为具体文本（periods为阶段对象数组）。"
            "不要将details字段平铺到structured_analysis，不添加别名或额外键。DEFERRED可以details={}，必须补问。"
            "quote必须逐字出现在同一对象的content中。其他fragment_key无需structured_analysis。\n"
            f"{json.dumps(required_structures, ensure_ascii=False)}\n"
        )
        if analysis_context.get("step_key") == "S4":
            resource_keys = [f["finding_key"] for f in analysis_context.get("upstream_confirmed_findings", [])
                             if f.get("semantic_role") in RESOURCE_ROLES]
            structure_note += (
                "每项ACTION.structured_data.reasoning_path.resource_refs必须从以下已确认资源ID中选择，"
                "不要引用analysis片段ID、PERSONA、BLOCK或改名ID。block_refs则逐字引用本批次或上游的BLOCK Finding。\n"
                f"{json.dumps(resource_keys, ensure_ascii=False)}\n"
            )
    reference_catalog = {
        "evidence_keys": [
            item["evidence_key"]
            for item in analysis_context.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("evidence_key"), str)
        ],
        "confirmed_finding_keys": [
            item["finding_key"]
            for item in analysis_context.get("upstream_confirmed_findings", [])
            if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
        ],
    }
    relation_rule = (
        "relation_refs可引用confirmed_finding_keys中的已确认上游Finding；"
        "reasoning_contract存在时也可引用同一批次候选的key（先审核保存资源/卡点，再保存行动）。"
        if analysis_context.get("reasoning_contract") else
        "relation_refs只能引用confirmed_finding_keys中的已确认上游Finding。"
    )
    system_prompt = (
        f"{GLOBAL_POLICY}\n\n【任务类型】\n"
        "你正在生成咨询师内部审核用的分析候选，不是在写最终报告。"
        "只输出符合契约的严格 JSON；不能输出 Markdown、推理过程或输入之外的事实。\n\n"
        "【机器可读输出契约】\n必须返回所有 required 字段；没有候选时对应字段使用空数组。"
        "数组中每个对象的字段必须符合以下结构，不要改名或省略必填字段：\n"
        f"{output_contract}\n\n"
        "【允许使用的引用 ID】\n"
        "evidence_refs 只能逐字复制 evidence_keys 中的 ID；"
        f"{relation_rule}"
        "格式为 {\"finding_key\": \"原样 ID\"}。不得根据描述、标签或记忆编造 ID。"
        "analysis_fragments 和 risk_flags 也只能引用本列表、当前候选 Finding 的 ID。\n"
        f"{json.dumps(reference_catalog, ensure_ascii=False)}\n\n"
        f"【Skill Instructions】\n{instructions}{structure_note}{runtime_note}"
        f"{_example_guidance(context.get('few_shot_examples') or [])}"
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
            if semantic_model.get("reasoning_contract"):
                validate_priority_blocks(candidate, semantic_model)
        return

    if processor == "reports.validator":
        qa_input = (context.get("context") or {}).get("qa_input") or {}
        if qa_input.get("framework_contract"):
            review = normalize_framework_review(output.get("framework_review"), qa_input["framework_contract"],
                qa_input.get("content_plan") or {}, qa_input.get("report_fragments") or [])
            output["framework_review"] = review
            for item in review:
                if item["status"] == "MISSING":
                    output.setdefault("issues", []).append({"issue_type": "FRAMEWORK_CONTENT_MISSING", "severity": "BLOCK",
                        "target_fragment_key": item["fragment_keys"][0], "message": f'{item["requirement_id"]}：{item["reason"]}',
                        "evidence": item["quote"], "suggestion": "补齐已审核依据与正文内容，或明确暂缓并补问，然后重新校准。"})
        if qa_input.get("scorecard_required"):
            keys = {item["fragment_key"] for item in qa_input.get("report_fragments", [])}
            scorecard = validate_scorecard(output.get("scorecard"), keys)
            if not scorecard["passes_threshold"]:
                output.setdefault("issues", []).append({"issue_type": "quality_score_below_threshold", "severity": "BLOCK", "target_fragment_key": None, "message": "报告未达到总分80、事实16及安全8分的交付门槛。", "evidence": f'七维总分：{scorecard["total"]}/100', "suggestion": "修正低分维度并重新运行全文校准。"})
        issues = output.get("issues")
        if not isinstance(issues, list) or len(issues) > 100:
            raise ValueError("validator_issues_invalid")
        for issue in issues:
            if not isinstance(issue, dict):
                raise ValueError("validator_issue_invalid")
            if issue.get("severity") not in {"BLOCK", "MAJOR", "MINOR", "WARN", "SUGGESTION"}:
                raise ValueError("validator_issue_severity_invalid")
            for field in ("issue_type", "message", "evidence", "suggestion"):
                value = issue.get(field)
                if not isinstance(value, str) or not value.strip() or len(value) > 5000:
                    raise ValueError("validator_issue_invalid")
            target = issue.get("target_fragment_key")
            if target is not None and (not isinstance(target, str) or len(target) > 200):
                raise ValueError("validator_issue_target_invalid")
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
    if not used_findings and not used_fragments:
        raise ValueError("report_fragment_unsupported_finding")
    requirements = (context_data.get("fragment_allocation") or {}).get("requirements") or []
    if requirements:
        output["requirement_coverage"] = normalize_requirement_coverage(
            output.get("requirement_coverage"), requirements, output["content"])


def _validate_analysis_draft_output(
    output: dict[str, Any], context: dict[str, Any]
) -> None:
    analysis_context = context.get("analysis_context") or {}
    if analysis_context.get("step_key") not in {"S1", "S2", "S3", "S4"}:
        raise ValueError("report_analysis_step_invalid")
    if not isinstance(output.get("summary"), str) or not output["summary"].strip():
        raise ValueError("report_analysis_summary_invalid")
    findings = output.get("findings")
    fragments = output.get("analysis_fragments")
    risk_flags = output.get("risk_flags")
    if not isinstance(findings, list) or len(findings) > 20:
        raise ValueError("report_analysis_findings_invalid")
    if not isinstance(fragments, list) or len(fragments) > 20:
        raise ValueError("report_analysis_fragments_invalid")
    if not isinstance(risk_flags, list) or len(risk_flags) > 20:
        raise ValueError("report_analysis_risk_flags_invalid")

    evidence_keys = {
        item.get("evidence_key")
        for item in analysis_context.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("evidence_key"), str)
    }
    confirmed_finding_keys = {
        item.get("finding_key")
        for item in analysis_context.get("upstream_confirmed_findings", [])
        if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
    }
    finding_keys: set[str] = set()
    local_relation_keys = {f.get("finding_key") for f in findings if isinstance(f, dict) and isinstance(f.get("finding_key"), str)} if analysis_context.get("reasoning_contract") else set()
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError("report_analysis_finding_invalid")
        key = item.get("finding_key")
        claim = item.get("claim")
        role = item.get("semantic_role")
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", key)
            or key in finding_keys
            or not isinstance(claim, str)
            or not claim.strip()
            or len(claim) > 5000
            or not isinstance(role, str)
            or not role.strip()
            or len(role) > 48
            or item.get("kind") not in {"FINDING", "SIGNAL"}
            or item.get("confidence") not in {"LOW", "MEDIUM", "HIGH"}
            or item.get("importance") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            or item.get("reportability")
            not in {"INTERNAL_ONLY", "OPTIONAL", "RECOMMENDED", "MUST_INCLUDE"}
        ):
            raise ValueError("report_analysis_finding_invalid")
        finding_keys.add(key)
        evidence_refs = item.get("evidence_refs")
        relation_refs = item.get("relation_refs")
        if (
            not isinstance(evidence_refs, list)
            or any(not isinstance(ref, str) or ref not in evidence_keys for ref in evidence_refs)
            or not isinstance(relation_refs, list)
        ):
            raise ValueError("report_analysis_finding_reference_invalid")
        if not evidence_refs and not relation_refs:
            raise ValueError("report_analysis_finding_support_required")
        for relation in relation_refs:
            target = relation.get("finding_key") if isinstance(relation, dict) else relation
            if not isinstance(target, str) or target not in confirmed_finding_keys | local_relation_keys or target == key:
                raise ValueError("report_analysis_finding_reference_invalid")
        if not isinstance(item.get("structured_data"), dict):
            raise ValueError("report_analysis_finding_invalid")

    valid_finding_refs = confirmed_finding_keys | finding_keys
    fragment_keys: set[str] = set()
    for item in fragments:
        if not isinstance(item, dict):
            raise ValueError("report_analysis_fragment_invalid")
        key = item.get("fragment_key")
        content = item.get("content")
        title = item.get("title")
        finding_refs = item.get("finding_refs")
        evidence_refs = item.get("evidence_refs")
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", key)
            or key in fragment_keys
            or not isinstance(content, str)
            or not content.strip()
            or len(content) > 30000
            or (title is not None and (not isinstance(title, str) or len(title) > 240))
            or not isinstance(finding_refs, list)
            or any(not isinstance(ref, str) or ref not in valid_finding_refs for ref in finding_refs)
            or not isinstance(evidence_refs, list)
            or any(not isinstance(ref, str) or ref not in evidence_keys for ref in evidence_refs)
            or not finding_refs and not evidence_refs
        ):
            raise ValueError("report_analysis_fragment_invalid")
        fragment_keys.add(key)
        if analysis_context.get("framework_contract"):
            item["framework_coverage"] = normalize_coverage(item.get("framework_coverage"), content, allow_not_applicable=True)
        if analysis_context.get("reasoning_contract") and key in ANALYSIS_STRUCTURES:
            validate_reasoning_contract(analysis_context["reasoning_contract"])
            item["structured_analysis"] = normalize_structured_analysis(key, item.get("structured_analysis"), content)
            if key == "analysis.s3.timeline":
                validate_timeline_source(item["structured_analysis"], analysis_context.get("evidence", []), set(evidence_refs))

    required_topics = (analysis_context.get("sop_contract") or {}).get("topics") or []
    if any(topic["fragment_key"] not in fragment_keys for topic in required_topics):
        raise ValueError("report_analysis_sop_coverage_required")
    if required_topics and analysis_context.get("step_key") == "S4":
        validate_growth_experiments(findings, analysis_context.get("upstream_confirmed_findings", []),
                                    require_actions=bool(analysis_context.get("framework_contract")))
        if analysis_context.get("reasoning_contract"):
            validate_action_reasoning([*analysis_context.get("upstream_confirmed_findings", []), *findings], evidence_keys,
                reality_keys={e.get("evidence_key") for e in analysis_context.get("evidence", []) if isinstance(e, dict) and e.get("source_type") == "USER_PROVIDED"})

    for flag in risk_flags:
        if (
            not isinstance(flag, dict)
            or not isinstance(flag.get("message"), str)
            or not flag["message"].strip()
            or not isinstance(flag.get("references"), list)
        ):
            raise ValueError("report_analysis_risk_flag_invalid")
        references = flag["references"]
        if any(
            not isinstance(ref, str) or ref not in evidence_keys | valid_finding_refs
            for ref in references
        ):
            raise ValueError("report_analysis_risk_flag_invalid")


def _sanitize_analysis_draft_references(
    output: dict[str, Any], context: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, int]]:
    """Remove unsupported citations without retaining unsupported candidates."""
    analysis_context = context.get("analysis_context") or {}
    evidence_keys = {
        item.get("evidence_key")
        for item in analysis_context.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("evidence_key"), str)
    }
    confirmed_finding_keys = {
        item.get("finding_key")
        for item in analysis_context.get("upstream_confirmed_findings", [])
        if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
    }
    sanitized = deepcopy(output)
    local_relation_keys = {f.get("finding_key") for f in sanitized.get("findings", []) if isinstance(f, dict) and isinstance(f.get("finding_key"), str)} if analysis_context.get("reasoning_contract") and isinstance(sanitized.get("findings"), list) else set()
    repairs = {
        "invalid_evidence_refs_removed": 0,
        "invalid_finding_refs_removed": 0,
        "invalid_risk_refs_removed": 0,
        "unsupported_findings_dropped": 0,
        "unsupported_fragments_dropped": 0,
        "unsupported_risk_flags_dropped": 0,
    }

    findings = sanitized.get("findings")
    if not isinstance(findings, list):
        return sanitized, repairs
    retained_findings = []
    for item in findings:
        if not isinstance(item, dict):
            retained_findings.append(item)
            continue
        evidence_refs = item.get("evidence_refs")
        relation_refs = item.get("relation_refs")
        if not isinstance(evidence_refs, list) or not isinstance(relation_refs, list):
            retained_findings.append(item)
            continue
        valid_evidence_refs = [
            ref for ref in evidence_refs if isinstance(ref, str) and ref in evidence_keys
        ]
        valid_relation_refs = []
        for ref in relation_refs:
            target = ref.get("finding_key") if isinstance(ref, dict) else ref
            if isinstance(target, str) and target in confirmed_finding_keys | local_relation_keys:
                valid_relation_refs.append(ref)
        repairs["invalid_evidence_refs_removed"] += len(evidence_refs) - len(valid_evidence_refs)
        repairs["invalid_finding_refs_removed"] += len(relation_refs) - len(valid_relation_refs)
        item["evidence_refs"] = valid_evidence_refs
        item["relation_refs"] = valid_relation_refs
        if not valid_evidence_refs and not valid_relation_refs:
            repairs["unsupported_findings_dropped"] += 1
            continue
        retained_findings.append(item)
    sanitized["findings"] = retained_findings

    valid_finding_keys = confirmed_finding_keys | {
        item.get("finding_key")
        for item in retained_findings
        if isinstance(item, dict) and isinstance(item.get("finding_key"), str)
    }
    fragments = sanitized.get("analysis_fragments")
    if isinstance(fragments, list):
        retained_fragments = []
        for item in fragments:
            if not isinstance(item, dict):
                retained_fragments.append(item)
                continue
            finding_refs = item.get("finding_refs")
            evidence_refs = item.get("evidence_refs")
            if not isinstance(finding_refs, list) or not isinstance(evidence_refs, list):
                retained_fragments.append(item)
                continue
            valid_finding_refs = [
                ref for ref in finding_refs if isinstance(ref, str) and ref in valid_finding_keys
            ]
            valid_evidence_refs = [
                ref for ref in evidence_refs if isinstance(ref, str) and ref in evidence_keys
            ]
            repairs["invalid_finding_refs_removed"] += len(finding_refs) - len(valid_finding_refs)
            repairs["invalid_evidence_refs_removed"] += len(evidence_refs) - len(valid_evidence_refs)
            item["finding_refs"] = valid_finding_refs
            item["evidence_refs"] = valid_evidence_refs
            if not valid_finding_refs and not valid_evidence_refs:
                repairs["unsupported_fragments_dropped"] += 1
                continue
            retained_fragments.append(item)
        sanitized["analysis_fragments"] = retained_fragments

    risk_flags = sanitized.get("risk_flags")
    if isinstance(risk_flags, list):
        retained_flags = []
        valid_references = evidence_keys | valid_finding_keys
        for item in risk_flags:
            if not isinstance(item, dict) or not isinstance(item.get("references"), list):
                retained_flags.append(item)
                continue
            references = item["references"]
            filtered_references = [
                ref for ref in references if isinstance(ref, str) and ref in valid_references
            ]
            repairs["invalid_risk_refs_removed"] += len(references) - len(filtered_references)
            item["references"] = filtered_references
            if references and not filtered_references:
                repairs["unsupported_risk_flags_dropped"] += 1
                continue
            retained_flags.append(item)
        sanitized["risk_flags"] = retained_flags

    return sanitized, {key: count for key, count in repairs.items() if count}


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
    if processor == "reports.analysis_draft":
        stage_key = (context.get("analysis_context") or {}).get("step_key")
        expected_stage = specification["instructions"].get("stage_key")
        if stage_key != expected_stage:
            raise ValueError("report_analysis_skill_stage_mismatch")
    if processor == "reports.single_step" and "reports.calculate_mingli_foundation" not in specification["tool_policy"].get("allowed", []):
        raise ValueError("skill_required_tool_not_allowed")
    if processor not in {"reports.single_step", "reports.analysis_draft", "reports.narrative_candidates", "reports.fragment_authoring", "reports.validator"}:
        raise ValueError("skill_processor_unsupported")
    profile = context.get("profile") or {}
    context_data = context.get("context") or {}
    missing_context = [
        field
        for field in specification["context_policy"].get("required", [])
        if context_data.get(field) in (None, "", [], {})
        and not (field == "continuity" and isinstance(context_data.get(field), dict))
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
    elif processor == "reports.analysis_draft":
        system_prompt, user_prompt = _analysis_prompts(
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
    if completion.trace.get("finish_reason") == "length":
        trace.update(output_validation="failed", error_type="TruncatedOutput")
        raise SkillExecutionError("skill_output_truncated", trace)
    try:
        output = (
            parse_ai_response(
                completion.content, {**profile, "foundation_data": foundation}
            )
            if processor == "reports.single_step"
            else _parse_json_output(completion.content)
        )
        _validate_output(output, completion.content, specification)
        if processor == "reports.analysis_draft":
            output, reference_repairs = _sanitize_analysis_draft_references(
                output, context
            )
            _validate_analysis_draft_output(output, context)
            if reference_repairs:
                trace["reference_repairs"] = reference_repairs
        elif processor != "reports.single_step":
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
