from copy import deepcopy
from typing import Any


DEFAULT_SKILL_KEY = "report.generate"
GLOBAL_POLICY_VERSION = "global-policy-v1"

GLOBAL_POLICY = """Follow the skill instructions and preserve the user's agency.
Do not diagnose medical or mental-health conditions, present traditional
interpretations as clinical facts, predict certain future outcomes, invent user
experiences, or expose hidden reasoning. Treat examples as style guidance only;
never transfer facts from an example to the current user."""

ALLOWED_PROCESSORS = {"reports.single_step"}
ALLOWED_TOOLS = {"reports.calculate_mingli_foundation"}

DEFAULT_SKILL_SPECIFICATION: dict[str, Any] = {
    "identity": {
        "skill_key": DEFAULT_SKILL_KEY,
        "name": "人生说明书报告生成",
        "description": "基于已确认档案与本次申请情境生成结构化报告草稿。",
    },
    "input_contract": {
        "required": ["name", "gender", "birth_year", "birth_month", "birth_day"],
        "type": "object",
    },
    "context_policy": {
        "required": ["subject", "request"],
        "optional": ["facts", "runtime"],
        "forbidden": ["other_users", "internal_chain_of_thought"],
        "projection": "SELECT_FIELDS",
        "fields": ["profile", "context", "foundation_data"],
        "profile_fields": [
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
            "current_residence",
            "marital_status",
            "occupation_status",
            "highest_education",
            "mbti",
            "personality_keywords",
            "strengths",
            "limitations",
            "mingli_experience",
            "mingli_attitude",
            "preferred_content_depth",
        ],
        "context_fields": [
            "focus_topics",
            "current_challenge",
            "expected_outcomes",
            "issue_duration",
            "impact_level",
            "decision_status",
            "decision_description",
            "decision_style",
            "additional_info",
            "subject",
            "request",
        ],
    },
    "instructions": {
        "objective": "生成一份克制、具体、可供咨询师审校的人生说明书。",
        "methodology": [
            "使用确定性命理基础作为输入，不重新排盘。",
            "区分用户提供的事实与生成内容。",
            "每个重要判断说明依据，每条建议给出可执行动作。",
        ],
    },
    "knowledge_policy": {"snapshot": [], "retrieval": "NONE"},
    "example_policy": {"enabled": False, "max_examples": 0},
    "processor_policy": {"processor": "reports.single_step"},
    "tool_policy": {"allowed": ["reports.calculate_mingli_foundation"]},
    "model_policy": {
        "provider": "deepseek",
        "model": None,
        "temperature": 0.7,
        "max_tokens": 8000,
        "timeout_seconds": 120,
    },
    "output_contract": {
        "type": "object",
        "required": [
            "basic_info",
            "energy_profile",
            "career_guidance",
            "relationship_pattern",
            "personal_growth",
            "summary",
            "ai_generated_content",
        ],
        "properties": {
            "basic_info": {"type": "object"},
            "energy_profile": {"type": "object"},
            "career_guidance": {"type": "object"},
            "relationship_pattern": {"type": "object"},
            "personal_growth": {"type": "object"},
            "summary": {"type": "string"},
            "ai_generated_content": {"type": "string"},
        },
    },
    "guardrails": {
        "global_policy_version": GLOBAL_POLICY_VERSION,
        "blocked_phrases": ["注定发财", "必然离婚", "保证治愈"],
    },
    "evaluation_profile": {
        "metrics": ["schema", "source_fidelity", "safety", "style"],
        "minimum_score": 0.8,
    },
}


def validate_skill_specification(specification: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(specification, dict):
        raise ValueError("skill_specification_invalid")
    spec = deepcopy(specification)
    required_sections = (
        "identity",
        "input_contract",
        "context_policy",
        "instructions",
        "knowledge_policy",
        "example_policy",
        "processor_policy",
        "tool_policy",
        "model_policy",
        "output_contract",
        "guardrails",
        "evaluation_profile",
    )
    if any(not isinstance(spec.get(section), dict) for section in required_sections):
        raise ValueError("skill_specification_sections_required")

    identity = spec["identity"]
    skill_key = str(identity.get("skill_key") or "").strip()
    name = str(identity.get("name") or "").strip()
    if not skill_key or not name:
        raise ValueError("skill_identity_required")
    processor = spec["processor_policy"].get("processor")
    if processor not in ALLOWED_PROCESSORS:
        raise ValueError("skill_processor_required")
    if not isinstance(spec["model_policy"].get("provider"), str):
        raise ValueError("skill_model_provider_required")
    if spec["model_policy"]["provider"] != "deepseek":
        raise ValueError("skill_model_provider_unsupported")
    tools = spec["tool_policy"].get("allowed", [])
    if not isinstance(tools, list) or any(tool not in ALLOWED_TOOLS for tool in tools):
        raise ValueError("skill_tool_unsupported")
    required_output = spec["output_contract"].get("required")
    if (
        not isinstance(required_output, list)
        or not required_output
        or any(not isinstance(field, str) or not field for field in required_output)
        or len(set(required_output)) != len(required_output)
    ):
        raise ValueError("skill_output_contract_required")
    if spec["output_contract"].get("type", "object") != "object":
        raise ValueError("skill_output_type_unsupported")
    properties = spec["output_contract"].get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError("skill_output_properties_invalid")
    allowed_output_types = {"object", "array", "string", "number", "integer", "boolean"}
    if any(
        not isinstance(schema, dict) or schema.get("type") not in allowed_output_types
        for schema in properties.values()
    ):
        raise ValueError("skill_output_properties_invalid")
    for section, key in (
        ("input_contract", "required"),
        ("context_policy", "required"),
        ("context_policy", "optional"),
        ("context_policy", "forbidden"),
        ("context_policy", "fields"),
        ("context_policy", "profile_fields"),
        ("context_policy", "context_fields"),
    ):
        if key in spec[section] and not isinstance(spec[section][key], list):
            raise ValueError("skill_specification_list_invalid")

    projection = spec["context_policy"].get("projection", "SELECT_FIELDS")
    if projection not in {"FULL", "SUMMARY", "STRUCTURED_ONLY", "SELECT_FIELDS"}:
        raise ValueError("skill_context_projection_invalid")
    spec["context_policy"]["projection"] = projection
    model_policy = spec["model_policy"]
    try:
        temperature = float(model_policy.get("temperature", 0.7))
        max_tokens = int(model_policy.get("max_tokens", 8000))
        timeout_seconds = float(model_policy.get("timeout_seconds", 120))
    except (TypeError, ValueError):
        raise ValueError("skill_model_policy_invalid")
    if not 0 <= temperature <= 2 or not 1 <= max_tokens <= 16000:
        raise ValueError("skill_model_policy_invalid")
    if not 1 <= timeout_seconds <= 240:
        raise ValueError("skill_model_policy_invalid")
    if model_policy_version := spec["guardrails"].get("global_policy_version"):
        if model_policy_version != GLOBAL_POLICY_VERSION:
            raise ValueError("skill_global_policy_unsupported")
    elif "global_policy_version" in spec["guardrails"]:
        raise ValueError("skill_global_policy_unsupported")
    blocked_phrases = spec["guardrails"].get("blocked_phrases", [])
    if not isinstance(blocked_phrases, list) or any(
        not isinstance(phrase, str) for phrase in blocked_phrases
    ):
        raise ValueError("skill_guardrails_invalid")
    model_policy.update(
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )
    identity["skill_key"] = skill_key
    identity["name"] = name
    return spec


def default_skill_specification() -> dict[str, Any]:
    return validate_skill_specification(DEFAULT_SKILL_SPECIFICATION)
