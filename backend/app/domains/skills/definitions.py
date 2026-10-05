from copy import deepcopy
from typing import Any
from .analysis_sop import sop_methodology, stage_contract
from .report_knowledge import knowledge_for_stage
from app.domains.quality.scorecard import RUBRIC


DEFAULT_SKILL_KEY = "report.generate"
GLOBAL_POLICY_VERSION = "global-policy-v1"

GLOBAL_POLICY = """Follow the skill instructions and preserve the user's agency.
Do not diagnose medical or mental-health conditions, present traditional
interpretations as clinical facts, predict certain future outcomes, invent user
experiences, or expose hidden reasoning. Treat examples as style guidance only;
never transfer facts from an example to the current user."""

ALLOWED_PROCESSORS = {
    "calendar.production",
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
            "demo_assumptions",
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
            "usage_scenario",
            "analysis_date",
            "demo_assumptions",
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
    token_limit = 32768 if model_policy.get("thinking") is True else 16000
    if not 0 <= temperature <= 2 or not 1 <= max_tokens <= token_limit:
        raise ValueError("skill_model_policy_invalid")
    if not 1 <= timeout_seconds <= 240:
        raise ValueError("skill_model_policy_invalid")
    if "thinking" in model_policy and not isinstance(model_policy["thinking"], bool):
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
            "supporting_findings、deemphasized_findings 和 priority_blocks[].finding_refs 都必须逐字复制当前输入的 finding_key，不引用样例、分析片段编号或自行缩写。",
            "不得创建事实、Finding、置信度或覆盖人工确认。",
            "明确列出支持和弱化的 Finding，缺少依据时降低表达强度。",
            "输出严格 JSON，不附加 Markdown 或解释文字。",
        ],
    }
    candidates["tool_policy"] = {"allowed": []}
    candidates["example_policy"] = {"enabled": True, "max_examples": 3}
    candidates["instructions"]["methodology"].extend([
        "总叙事：心灵结构→认识自己→隐藏部分→卡点→保护功能→共性模式→整合能力→人生方向→成长实验。",
        "保持你是谁/卡在哪/往哪去三章分工，候选主线和标题必须围绕用户独特矛盾，避免固定模板。",
        "按S4已审核卡点选择优先4–5项（证据不足可3项），不得为了数量发明卡点。",
    ])
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
                        "supporting_findings": {"type": "array", "items": {"type": "string"}},
                        "deemphasized_findings": {"type": "array", "items": {"type": "string"}},
                        "priority_blocks": {"type": "array", "items": {"type": "object", "required": ["title", "finding_refs"], "properties": {"title": {"type": "string"}, "finding_refs": {"type": "array", "items": {"type": "string"}}}}},
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
    authoring["example_policy"] = {"enabled": True, "max_examples": 3}
    authoring["knowledge_policy"] = {"snapshot": knowledge_for_stage("S5"), "retrieval": "VERSION_SNAPSHOT"}
    authoring["instructions"]["methodology"].extend([
        "分配中有requirements时，逐项满足checks，并输出requirement_coverage数组。每项含requirement_id、status(FULFILLED/DEFERRED/MISSING)、reason、quote(正文逐字摘录)、follow_up_questions。核心项不得标不适用；资料不足需在正文明确暂缓并补问。引用ID或有小标题不代表内容完成。不得伪造覆盖。",
        "有requirements时，每个分配的analysis_refs与action_refs都须实际参与表达或说明暂缓边界，并完整列入used_analysis_fragments/used_actions；不能只声明覆盖而漏掉来源。",
        "required_finding_refs存在时，全部来源都须参与表达并列入used_findings：包括卡点、Action及已确认资源。以reasoning_path解释资源→调节功能→能力→现实缺口→整合任务→工具→实验，不靠笼统建议跳过推导。INTERNAL_ONLY资料只作推导旁证，不作为新的用户心理结论或直接发布内部分析原文。quote只从本输出content中连续摘录一句，不从输入资料或元数据中摘录。",
        "先区分原始自述、系统计算和解释性假设。原始自述可直接陈述；对保护功能、动机、因果的解释在引入时清楚限定，后续承接保留条件与反证，不能转成断言。不因Finding的解释是假设而否认用户已说出的自我观察。",
        "概览约250–400字，仅概览四层关系；不展开完整触发链与保护/代价。不要在每节使用相同的卡点预告，不知道实际相邻小节时不要写‘下一节’。原型必须给出可学习能力和适用边界；实验必须逐项说明承接卡点、现实时间预算和减量选择。",
        "使用第二人称，描述模式并说明保护功能，不评判、不诊断；先意识后潜意识，命理术语翻译成日常语言。",
        "章节首页输出一句有依据的关键结论和简短关系路径图（可用箭头文本）。卡点部分只解释场景/运作/保护/代价/整合邀请，具体解法留给往哪去。",
        "阶段地图须保留上游已确认的大运起止年份、阶段主题/能力/旧模式，以条件式表达未来。",
        "成长实验只转述已确认ACTION的动作、频率、耗时、观察、退出条件，3–5个即可。",
        "参考用户自报MBTI与明确的深入/简洁偏好调整理论密度、篇幅和隐喻量，不推断八维分数，不改变事实。",
        "结尾简短回扣哲学方向和用户现实，不堆安慰；署名金句只能逐字来自 skill_knowledge.quote_library 中 VERIFIED 条目，否则用不署名原创寄语。",
        "每个分配的分析来源都须转译或明确指出资料边界，不暴露SOP编号、内部ID或审核过程。",
        "按片段职责取用来源，不把来源中的整份总结、实验、金句都复制进每节。标题用读者语言，不能照抄purpose或‘语义线索’等内部说明。",
        "只有 report.direction.growth_experiments 完整写行动步骤/频率/耗时/观察/退出条件；其他片段至多一句指向该节。只有 report.ending 使用金句，其他节不引用金句。",
        "overview只概览主线，self_direction只点出方向，common_pattern只综合差异机制；三处均不重新展开卡点保护/代价。life_map只写时序、阶段和时义，不重复实验。ending简短收束，不重复卡点机制或动作。",
        "未自述的情绪、自动想法、惯常场景和保护功能必须持续用可能/假如/待核对表达；尤其不把不适、内疚、先答应、女贵人出现的频率当作已证实事实。",
    ])
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
            "requirement_coverage": {"type": "array"},
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
            "标为用户自述的每句话必须能回到问卷原文；‘自我不适’‘短期维持关系’等未直接表述的内容必须标为假设。额外紫微宫位没有咨询师选用依据时不调用。",
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
        spec["instructions"]["methodology"].extend([
            "每条 finding 都提供 short_title：8–20 字的中文关键词标签，概括其核心判断，供列表快速识别；详细依据仍写在 claim 中。",
            "控制输出预算，保证JSON完整：summary约120字，每个Finding.claim约40–120字，analysis_fragments.content每项约150–300字，结构化details每字段约25–80字。只在reasoning_contract列出的片段返回structured_analysis，其他片段不添加。引用必要Evidence，不复制上游整份总结；不以压缩为由漏掉规定片段或Action字段。",
            "新案例analysis_context.reasoning_contract存在时，其analysis_structures列出的片段必须提交structured_analysis={status,reason,quote,follow_up_questions,details}。details严格按该key的字段表，逐字段给依据和边界；FULFILLED全部字段齐全，DEFERRED可为空但须在正文明确暂缓并补问，不能用NOT_APPLICABLE删掉核心推导。阶段地图periods.start_year/end_year必须逐字采用已提供程序测算证据内bazi_facts.dayun的起止年份，并在该片段evidence_refs引用当前测算版本；资料不足用DEFERRED，禁止补造年份。",
            "新案例S4每项ACTION的structured_data.reasoning_path须有resource_refs(只指已确认RESOURCE/USEFUL_GOD/STRUCTURE/SELF_DIRECTION)、regulation_function、capacity、reality_gap、block_refs(与行动block_refs一致)、integration_task、tool(与method一致)、rationale、evidence_refs(现实自述依据)。逐项说明资源如何转成能力、回应哪些卡点和为何选此工具。真实生活依据不能用单独的命盘计算冒充。关联当前批次BLOCK时使用已有候选key；先列资源/卡点，再列行动便于审核保存。不虚构新的事实或补造心理经历。",
            "新案例analysis_context.framework_contract存在时，每个analysis_fragments对象须有framework_coverage：status(FULFILLED/DEFERRED/NOT_APPLICABLE/MISSING)、reason、quote、follow_up_questions。quote只能从该对象刚生成的content逐字选择连续一句，不能摘录未出现在本content中的问卷、上游分析或details文字；structured_analysis.quote同样如此。DEFERRED必须说明缺失输入并给补问；NOT_APPLICABLE必须有资料证明的理由。MISSING不能用于完成节点。",
            "S2 mapping明确产出意识自我/自我信念，并与面具和未被接纳的部分区分；S4 ACTION的block_refs只能引用semantic_role=BLOCK的判断。不得用别的角色代替卡点。",
        ])
        spec["example_policy"] = {"enabled": True, "max_examples": 3}
        spec["knowledge_policy"] = {"snapshot": knowledge_for_stage(step_key), "retrieval": "VERSION_SNAPSHOT"}
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
                            "short_title": {"type": "string"},
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
                            "framework_coverage": {"type": "object"},
                            "structured_analysis": {"type": "object"},
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
    spec["instructions"]["methodology"].extend([
        "最终qa_input.framework_contract存在时，额外输出framework_review：逐项检查全部report_requirements。每项含requirement_id、fragment_keys(其编排归属)、status(FULFILLED/DEFERRED/MISSING)、reason、quote(对应正文逐字摘录)、follow_up_questions。独立核对checks是否实际完成，不接受作者自报覆盖代替阅读。核心缺失标MISSING；暂缓必须在正文说明且有可回答补问。",
        "confirmed_semantics.reasoning_contract存在时，检查structured_analysis及Action.reasoning_path所记载的依据、反证和适配理由是否成立，并与正文逐项核对。链条字段齐全不代表推导正确；用神到调节功能、能力到现实缺口、整合任务到工具与实验须有具体解释。命盘是解释视角，不能代替现实自述。INTERNAL_ONLY来源仅用于审核推导，不能作为新增用户结论发表。",
        "最终校准核对：与审核命盘和核心机制有无冲突、编造经历、单一信号强人格结论、诊断、确定未来、科学化命理、内部矛盾、卡点重复给解法、第三章是否回应共性模式。",
        "检查同一核心观点换句话重复3次以上，标出应删除的 fragment_key；金句只能用已核验库。",
        "当 qa_input.scorecard_required=true 时必须额外返回 scorecard.dimensions，维度如下，每维度有 score、reason、fragment_keys（本次报告片段ID数组）。程序计算总分；不要用笼统通过代替逐维评分。",
        "最多返回15条确有证据的问题，每个message/evidence/suggestion控制在150字内，同类问题合并定位。转译允许合理意译，不要求每节重复全部来源信息；某项已在合适章节覆盖时不在其他节报缺失。",
        "VERIFIED金句条目允许署名引用，不要求额外授权；引号外标点不构成事实问题。不假设未列出的许可要求，不报告‘如果…才可能…’的假想缺陷。",
        "只审核读者实际看到的title/content，transition_hint等生产元数据不属于正文；章节顺序以content_plan.fragments[].sequence_no为准。实验可分别对应不同卡点，不要求每个实验回应所有卡点。",
        "严格区分 report_fragments 正文和 confirmed_semantics 内部分析。仅在正文计重复；不得把内部分析语句说成当前报告的原文。每条evidence必须逐字摘录定位片段的正文，不能转述或拼接。",
        "用户自述以application_context和Evidence为依据，不因缺少单独Finding否定问卷已明确提供的资料。‘没有家庭资料，早期印记暂缓’不是编造早期经历；明确提出可核对假设并保留反证，不因未经测评而报事实错误。",
        "严格区分用户自述事实与对它的解释：例如用户说独自散步时比较放松，这个自我观察可直接陈述，不能因资源解释Finding为假设而把原始自述也降为假设。明确的可能/或许/假如/可以借此观察，加上适用边界或反证，可构成充分的假设限定；不要求每句叠加‘假设可能’。只在实际越过来源边界时扣分，不能根据表达缺少某个固定词而判定违规。",
        "核验库署名引用只需实际准确的可识别出处，不要求正文宣告‘来自已核验库’或复述审核元数据。不得将解释性判断写成物理事实，也不得把明确否定确定论的句子误读为确定论。不要要求读者看到内部confidence或角色名称。",
    ])
    spec["instructions"]["scoring_rubric"] = RUBRIC
    spec["knowledge_policy"] = {"snapshot": knowledge_for_stage("S5"), "retrieval": "VERSION_SNAPSHOT"}
    spec["tool_policy"] = {"allowed": []}
    spec["model_policy"]["temperature"] = 0.1
    spec["example_policy"] = {"enabled": True, "max_examples": 2}
    spec["processor_policy"] = {"processor": "reports.validator"}
    spec["output_contract"] = {
        "type": "object",
        "required": ["issues"],
        "properties": {"issues": {"type": "array"}, "scorecard": {"type": "object"}, "framework_review": {"type": "array"}},
    }
    spec["guardrails"]["blocked_phrases"] = []
    spec["evaluation_profile"] = {
        "metrics": ["fact_fidelity", "semantic_consistency", "safety", "narrative", "action", "personalization"],
        "minimum_score": 0.8,
    }
    return validate_skill_specification(spec)
