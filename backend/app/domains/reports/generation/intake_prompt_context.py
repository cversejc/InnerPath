from typing import Any, Mapping

from app.services.intake_service import normalize_context


def context_for_prompt(context: Mapping[str, Any]) -> str:
    """Render current request context without exposing account contact data."""
    normalized = normalize_context(context)
    labels = (
        ("当前困惑", normalized.get("current_challenge")),
        ("期望获得", "、".join(normalized.get("expected_outcomes") or [])),
        ("困惑持续时间", normalized.get("issue_duration")),
        ("影响程度", normalized.get("impact_level")),
        ("重要决策状态", normalized.get("decision_status")),
        ("决策描述", normalized.get("decision_description")),
        ("决策方式", "、".join(normalized.get("decision_style") or [])),
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
        ("命理态度", "mingli_attitude"),
        ("内容偏好", "preferred_content_depth"),
    )
    lines = []
    for label, field in labels:
        value = profile.get(field)
        if isinstance(value, (list, tuple)):
            value = "、".join(str(item) for item in value if item)
        if value:
            lines.append(f"{label}：{value}")
    return "\n".join(lines)
