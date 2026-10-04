from typing import Any, Mapping

from app.services.intake_service import normalize_context


def context_for_prompt(context: Mapping[str, Any]) -> str:
    """Render current request context without exposing account contact data."""
    normalized = normalize_context(context)
    labels = (
        ("其他关注领域", normalized.get("focus_topics_other")),
        ("当前困惑", normalized.get("current_challenge")),
        ("期望获得", "、".join(normalized.get("expected_outcomes") or [])),
        ("其他期待", normalized.get("expected_outcomes_other")),
        ("困惑持续时间", normalized.get("issue_duration")),
        ("影响程度", normalized.get("impact_level")),
        ("重要决策状态", normalized.get("decision_status")),
        ("决策描述", normalized.get("decision_description")),
        ("决策方式", "、".join(normalized.get("decision_style") or [])),
        ("其他决策方式", normalized.get("decision_style_other")),
        ("补充说明", normalized.get("additional_info")),
    )
    lines = [f"{label}：{value}" for label, value in labels if value]
    return "\n".join(lines)


def profile_context_for_prompt(profile: Mapping[str, Any]) -> str:
    """Render only stable, analytical profile fields for an AI prompt."""
    labels = (
        ("当前居住地", "current_residence"),
        ("婚姻状态", "marital_status"),
        ("职业状态", "occupation_status"),
        ("学历", "highest_education"),
        ("MBTI", "mbti"),
        ("性格关键词", "personality_keywords"),
        ("优势", "strengths"),
        ("限制", "limitations"),
        ("命理体验", "mingli_experience"),
        ("其他命理体验", "mingli_experience_other"),
        ("命理态度", "mingli_attitude"),
        ("内容偏好", "preferred_content_depth"),
        ("常见使用场景", "default_usage_scenarios"),
        ("其他使用场景", "default_usage_scenarios_other"),
    )
    lines = []
    for label, field in labels:
        value = profile.get(field)
        if field == "mingli_experience_other" and "other" not in (profile.get("mingli_experience") or []):
            continue
        if field == "default_usage_scenarios_other" and "other" not in (profile.get("default_usage_scenarios") or []):
            continue
        if isinstance(value, (list, tuple)):
            value = "、".join(str(item) for item in value if item)
        if value:
            lines.append(f"{label}：{value}")
    return "\n".join(lines)
