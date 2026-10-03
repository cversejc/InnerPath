from copy import deepcopy
from typing import Any
from .analysis_sop import sop_methodology, stage_contract


DEFAULT_SKILL_KEY = "report.generate"
GLOBAL_POLICY_VERSION = "global-policy-v1"

GLOBAL_POLICY = """Follow the skill instructions and preserve the user's agency.
Do not diagnose medical or mental-health conditions, present traditional
interpretations as clinical facts, predict certain future outcomes, invent user
experiences, or expose hidden reasoning. Treat examples as style guidance only;
never transfer facts from an example to the current user."""

ALLOWED_PROCESSORS = {
    "reports.single_step",
    "reports.analysis_draft",
    "reports.narrative_candidates",
    "reports.fragment_authoring",
    "reports.validator",
}
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


def default_narrative_skill_specifications() -> list[dict[str, Any]]:
    base = deepcopy(DEFAULT_SKILL_SPECIFICATION)
    candidates = deepcopy(base)
    candidates["identity"] = {
        "skill_key": "report.narrative_plan",
        "name": "报告叙事方案候选",
        "description": "只基于已确认语义资产生成供咨询师选择的叙事候选。",
    }
    candidates["input_contract"] = {"required": [], "type": "object"}
    candidates["context_policy"]["required"] = ["semantic_model"]
    candidates["context_policy"]["context_fields"] = list(
        dict.fromkeys(candidates["context_policy"]["context_fields"] + ["semantic_model"])
    )
    candidates["instructions"] = {
        "objective": "提出 2 到 3 个彼此有差异、由确认 Finding 支持的报告叙事候选。",
        "methodology": [
            "只选择 semantic_model.findings 中的 finding_key，不重新分析用户。",
            "不得创建事实、Finding、置信度或覆盖人工确认。",
            "明确列出支持和弱化的 Finding，缺少依据时降低表达强度。",
            "输出严格 JSON，不附加 Markdown 或解释文字。",
        ],
    }
    candidates["tool_policy"] = {"allowed": []}
    candidates["processor_policy"] = {"processor": "reports.narrative_candidates"}
    candidates["output_contract"] = {
        "type": "object",
        "required": ["candidates"],
        "properties": {
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "candidate_key",
                        "theme",
                        "rationale",
                        "supporting_findings",
                        "deemphasized_findings",
                        "priority_blocks",
                        "narrative_arc",
                    ],
                    "properties": {
                        "candidate_key": {"type": "string"},
                        "theme": {"type": "string"},
                        "rationale": {"type": "string"},
                        "supporting_findings": {"type": "array"},
                        "deemphasized_findings": {"type": "array"},
                        "priority_blocks": {"type": "array"},
                        "narrative_arc": {"type": "array"},
                    },
                },
            }
        },
    }

    authoring = deepcopy(base)
    authoring["identity"] = {
        "skill_key": "report.fragment_authoring",
        "name": "报告片段写作",
        "description": "根据已确认语义与咨询师确认的 NarrativePlan 撰写单个报告片段。",
    }
    authoring["input_contract"] = {"required": [], "type": "object"}
    authoring["context_policy"]["required"] = [
        "semantic_model",
        "narrative_plan",
        "fragment_request",
        "fragment_allocation",
        "continuity",
    ]
    authoring["context_policy"]["context_fields"] = list(
        dict.fromkeys(
            authoring["context_policy"]["context_fields"]
            + [
                "semantic_model",
                "narrative_plan",
                "fragment_request",
                "fragment_allocation",
                "continuity",
            ]
        )
    )
    authoring["instructions"] = {
        "objective": "仅根据确认语义与已确认 NarrativePlan 写作一个完整、可审校的报告小节。",
        "methodology": [
            "只允许选择、组织、转译和表达输入中的已确认内容。",
            "严格遵循 fragment_allocation 中的 finding_refs、analysis_refs、action_refs、must_cover 和 new_information_role。",
            "不得读取或推测分配范围外的 Case 内容；must_not_repeat 是硬性约束。",
            "只将 continuity 视为写作衔接提示，不把它当成新的语义来源。",
            "不得创建事实、Finding、心理结论、行动建议或改变专业判断。",
            "若缺少语义支撑，返回 MISSING_SEMANTIC_SUPPORT 且不补写结论。",
            "列出 used_findings 与 used_analysis_fragments 的稳定标识。",
            "输出严格 JSON，不附加 Markdown 或解释文字。",
        ],
    }
    authoring["tool_policy"] = {"allowed": []}
    authoring["processor_policy"] = {"processor": "reports.fragment_authoring"}
    authoring["output_contract"] = {
        "type": "object",
        "required": [
            "status",
            "title",
            "content",
            "used_findings",
            "used_analysis_fragments",
            "used_actions",
            "transition_hint",
            "presentation_meta",
        ],
        "properties": {
            "status": {
                "type": "string",
                "enum": ["READY_FOR_REVIEW", "MISSING_SEMANTIC_SUPPORT"],
                "description": "内容可审阅时使用 READY_FOR_REVIEW；缺少来源支持时使用 MISSING_SEMANTIC_SUPPORT。",
            },
            "title": {"type": "string"},
            "content": {"type": "string"},
            "used_findings": {"type": "array"},
            "used_analysis_fragments": {"type": "array"},
            "used_actions": {"type": "array"},
            "transition_hint": {"type": "string"},
            "presentation_meta": {"type": "object"},
        },
    }
    return [validate_skill_specification(candidates), validate_skill_specification(authoring)]


ANALYSIS_STEPS: dict[str, dict[str, Any]] = {
    "S1": {
        "skill_key": "report.s1_foundation_analysis",
        "name": "S1 命理基础结构分析",
        "objective": "整理系统计算的命理基础，形成可供咨询师审核的结构判断与待验证信号。",
        "methodology": [
            "只解释输入中的确定性命理计算结果，不自行排盘或补充缺失数据。",
            "将传统命理解释明确标为解释视角，不写成客观事实或确定性预测。",
            "可以提出待 S2 验证的心理 Signal，但不得在 S1 将其写成心理诊断或定论。",
            "每项判断至少引用一条输入 Evidence；无证据时不生成该判断。",
            "分析片段只用于咨询师审阅，不是给用户的报告正文。",
        ],
    },
    "S2": {
        "skill_key": "report.s2_psychology_mapping",
        "name": "S2 心理映射分析",
        "objective": "基于用户 Evidence 与已确认的 S1 结构，提出可审阅的心理运作模式假设。",
        "methodology": [
            "心理结论必须作为可验证的运作模式假设，不得诊断心理或精神疾病。",
            "区分用户直接表达、S1 命理解释与本阶段的心理映射。",
            "优先说明触发情境、自动想法、情绪、应对方式及保护功能；输入不足时明确保留不确定性。",
            "只能引用输入中的 Evidence 和已确认上游 Finding，不把未确认内容当作事实。",
            "分析片段只用于咨询师审阅，不是给用户的报告正文。",
        ],
    },
    "S3": {
        "skill_key": "report.s3_integration",
        "name": "S3 命理心理哲学整合",
        "objective": "综合已确认的命理与心理判断，提出中心张力、自我方向和整合任务候选。",
        "methodology": [
            "整合已确认的上游 Finding，不重复执行 S1 命理分析或 S2 心理映射。",
            "明确指出整合判断引用的上游 Finding 与 Evidence。",
            "描述需要发展的能力与两端张力，不塑造完美人格，也不预测必然结果。",
            "输入不足或上游判断冲突时，将其列为待咨询师核查的风险，不自行消解冲突。",
            "分析片段只用于咨询师审阅，不是给用户的报告正文。",
        ],
    },
    "S4": {
        "skill_key": "report.s4_mechanism_block_action",
        "name": "S4 机制卡点与行动",
        "objective": "将已确认的上游语义组织为可核查的运作机制、关键卡点与低风险行动候选。",
        "methodology": [
            "解释模式可能发挥的保护功能、触发条件和长期代价，不将其描述成缺陷或诊断。",
            "优先提出可逆、具体、低成本且可复盘的行动，不替用户作重大决定。",
            "每项机制、卡点或行动都必须引用已确认的 Finding 或 Evidence。",
            "行动与专业判断分开表述；不得在本阶段创造缺少来源的新事实。",
            "分析片段只用于咨询师审阅，不是给用户的报告正文。",
        ],
    },
}


def default_analysis_skill_specifications() -> list[dict[str, Any]]:
    specifications = []
    for step_key, stage in ANALYSIS_STEPS.items():
        spec = deepcopy(DEFAULT_SKILL_SPECIFICATION)
        spec["identity"] = {
            "skill_key": stage["skill_key"],
            "name": stage["name"],
            "description": stage["objective"],
        }
        spec["input_contract"] = {"required": [], "type": "object"}
        spec["context_policy"] = {
            "required": [],
            "optional": [],
            "forbidden": ["other_users", "internal_chain_of_thought"],
            "projection": "FULL",
        }
        spec["instructions"] = {
            "objective": stage["objective"],
            "methodology": stage["methodology"] + sop_methodology(step_key),
            "stage_key": step_key,
            "sop_contract": stage_contract(step_key),
        }
        spec["example_policy"] = {"enabled": True, "max_examples": 3}
        spec["processor_policy"] = {"processor": "reports.analysis_draft"}
        spec["tool_policy"] = {"allowed": []}
        spec["model_policy"].update(temperature=0.35, max_tokens=12000)
        spec["output_contract"] = {
            "type": "object",
            "required": ["summary", "findings", "analysis_fragments", "risk_flags"],
            "properties": {
                "summary": {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "finding_key",
                            "claim",
                            "kind",
                            "semantic_role",
                            "confidence",
                            "importance",
                            "reportability",
                            "evidence_refs",
                            "relation_refs",
                            "structured_data",
                        ],
                        "properties": {
                            "finding_key": {"type": "string"},
                            "claim": {"type": "string"},
                            "kind": {"type": "string", "enum": ["FINDING", "SIGNAL"]},
                            "semantic_role": {"type": "string"},
                            "confidence": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                            "importance": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                            "reportability": {
                                "type": "string",
                                "enum": ["INTERNAL_ONLY", "OPTIONAL", "RECOMMENDED", "MUST_INCLUDE"],
                            },
                            "evidence_refs": {"type": "array", "items": {"type": "string"}},
                            "relation_refs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["finding_key"],
                                    "properties": {"finding_key": {"type": "string"}},
                                },
                            },
                            "structured_data": {"type": "object"},
                        },
                    },
                },
                "analysis_fragments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "fragment_key",
                            "title",
                            "content",
                            "finding_refs",
                            "evidence_refs",
                        ],
                        "properties": {
                            "fragment_key": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "finding_refs": {"type": "array", "items": {"type": "string"}},
                            "evidence_refs": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "risk_flags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["message", "references"],
                        "properties": {
                            "message": {"type": "string"},
                            "references": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        }
        spec["guardrails"] = {
            "global_policy_version": GLOBAL_POLICY_VERSION,
            "blocked_phrases": ["注定发财", "必然离婚", "保证治愈"],
        }
        spec["evaluation_profile"] = {
            "metrics": ["schema", "source_fidelity", "safety", "stage_fit"],
            "minimum_score": 0.8,
        }
        specifications.append(validate_skill_specification(spec))
    return specifications


def default_validator_skill_specification() -> dict[str, Any]:
    spec = deepcopy(DEFAULT_SKILL_SPECIFICATION)
    spec["identity"] = {
        "skill_key": "report.final_validator",
        "name": "报告语义质量审核",
        "description": "检查已组装报告的事实忠实度、安全、语义一致性、叙事和行动质量，并给出可定位的问题。",
    }
    spec["input_contract"] = {"required": [], "type": "object"}
    spec["context_policy"] = {
        "required": ["qa_input"],
        "optional": [],
        "forbidden": ["internal_chain_of_thought", "other_users"],
        "projection": "SELECT_FIELDS",
        "fields": ["profile", "context"],
        "profile_fields": ["name"],
        "context_fields": ["qa_input"],
    }
    spec["instructions"] = {
        "objective": "检查报告内容是否忠实于已确认的 Finding 和用户提供情境，并评估安全、跨章节一致性、叙事质量、行动质量和个性化。",
        "methodology": [
            "严格只执行 qa_input.validation_scope 明确列出的检查；chapter_key 存在时只检查该章已提供的片段。",
            "只报告有明确片段和证据的可修复问题，不重写报告。",
            "章节检查关注本章的阅读顺序、段落衔接、重复、章节职责和来源覆盖。全文检查关注核心暗线、跨章一致性、Finding 覆盖、卡点到行动关系及开头结尾呼应。",
            "将问题定位到具体 fragment_key；不要把全篇问题自动改写成正文。",
            "不得根据命理或心理内容作诊断或确定性预测。",
            "问题必须包含 issue_type、severity、message、evidence 和 suggestion；片段无法定位时 target_fragment_key 返回 null。",
            "severity 只能为 BLOCK、MAJOR 或 MINOR。无问题时返回空 issues。",
            "只输出严格 JSON。",
        ],
    }
    spec["tool_policy"] = {"allowed": []}
    spec["processor_policy"] = {"processor": "reports.validator"}
    spec["output_contract"] = {
        "type": "object",
        "required": ["issues"],
        "properties": {"issues": {"type": "array"}},
    }
    spec["guardrails"]["blocked_phrases"] = []
    spec["evaluation_profile"] = {
        "metrics": ["fact_fidelity", "semantic_consistency", "safety", "narrative", "action", "personalization"],
        "minimum_score": 0.8,
    }
    return validate_skill_specification(spec)
