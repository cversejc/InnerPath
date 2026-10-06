import re
from typing import Any, Dict


def extract_chat_content(response_data: Dict[str, Any]) -> str:
    """Extract visible assistant content from a chat-completions response."""
    choices = response_data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ValueError("模型服务响应缺少 choices")

    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None

    if isinstance(content, str):
        normalized_content = content.strip()
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        normalized_content = "".join(parts).strip()
    else:
        normalized_content = ""

    if not normalized_content:
        finish_reason = choice.get("finish_reason", "unknown")
        raise ValueError(f"模型服务返回空正文，finish_reason={finish_reason}")

    return normalized_content


def parse_ai_response(ai_content: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert generated report text into the structured report fields."""
    return {
        "basic_info": {
            "name": user_data.get("name", ""),
            "birth_date": (
                f"{user_data.get('birth_year')}-{user_data.get('birth_month')}-"
                f"{user_data.get('birth_day')}"
            ),
            "report_date": None,
            "generated_by": "AI",
        },
        "ai_generated_content": ai_content,
        "energy_profile": extract_energy_profile(ai_content),
        "career_guidance": extract_career_guidance(ai_content),
        "relationship_pattern": extract_relationship_pattern(ai_content),
        "personal_growth": extract_personal_growth(ai_content),
        "summary": extract_summary(ai_content),
    }


def extract_energy_profile(content: str) -> Dict[str, Any]:
    """Extract energy profile labels from report text."""
    type_match = re.search(r"能量类型[：:]\s*([^\n]+)", content)
    traits_match = re.search(r"核心特质[：:]\s*([^\n]+)", content)

    return {
        "type": type_match.group(1).strip() if type_match else "综合型",
        "core_traits": (
            traits_match.group(1).strip() if traits_match else "独特的个人特质"
        ),
        "description": content[:200] + "..." if len(content) > 200 else content,
    }


def extract_career_guidance(content: str) -> Dict[str, Any]:
    """Provide default career guidance when no structured fields are present."""
    return {
        "suitable_paths": ["创意型工作", "分析型工作", "人际型工作"],
        "work_style": "根据个人特质灵活调整",
        "development_suggestions": ["持续学习", "拓展人脉", "发挥优势"],
    }


def extract_relationship_pattern(content: str) -> Dict[str, Any]:
    """Provide default relationship guidance when no structured fields are present."""
    return {
        "style": "独特的关系互动模式",
        "strengths": ["真诚", "理解", "支持"],
        "challenges": ["需要学习的方面"],
        "growth_direction": "持续成长和改善",
    }


def extract_personal_growth(content: str) -> Dict[str, Any]:
    """Provide default personal growth guidance when no structured fields are present."""
    return {
        "current_issues": ["当前关注的议题"],
        "action_plan": [
            {
                "area": "能量管理",
                "action": "每天预留时间进行自我觉察",
                "timeline": "立即开始",
            }
        ],
        "resources": ["推荐阅读", "推荐工具", "推荐实践"],
    }


def extract_summary(content: str) -> str:
    """Extract the closing section, or return the existing default summary."""
    summary_match = re.search(r"##\s*五、总结与寄语([\s\S]*?)$", content)
    return (
        summary_match.group(1).strip()
        if summary_match
        else "你是独特的个体，拥有无限的成长潜力。"
    )
