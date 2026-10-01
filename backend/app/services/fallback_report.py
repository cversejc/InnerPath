from typing import Any, Dict

from app.core.logging_config import get_logger

logger = get_logger("app.services.ai_service")


def generate_basic_report(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a deterministic basic report when AI generation is unavailable."""
    logger.info("使用基础算法生成报告（降级方案）")

    birth_year = user_data.get("birth_year", 2000)
    birth_month = user_data.get("birth_month", 1)
    birth_day = user_data.get("birth_day", 1)
    selected_topics = user_data.get("selected_topics", [])

    logger.debug(f"出生日期: {birth_year}-{birth_month}-{birth_day}")

    sum_val = (int(birth_year) + int(birth_month) + int(birth_day)) % 5
    elements = ["wood", "fire", "earth", "metal", "water"]
    dominant_element = elements[sum_val]

    logger.info(f"主导五行: {dominant_element}")

    energy_types = {
        "wood": {
            "name": "生长驱动型",
            "traits": "创新求变、积极进取、富有创造力",
            "description": "你的能量倾向于向外扩展和生长，喜欢探索新事物，具有强烈的成长动力。",
        },
        "fire": {
            "name": "表达驱动型",
            "traits": "热情洋溢、善于表达、富有感染力",
            "description": "你的能量倾向于向外散发和表达，喜欢与人互动，具有强烈的表现欲。",
        },
        "earth": {
            "name": "稳定承载型",
            "traits": "踏实稳重、包容接纳、注重安全",
            "description": "你的能量倾向于稳定和承载，喜欢建立秩序，具有强烈的责任感。",
        },
        "metal": {
            "name": "秩序驱动型",
            "traits": "理性客观、追求完美、注重规则",
            "description": "你的能量倾向于收敛和精炼，喜欢建立标准，具有强烈的原则性。",
        },
        "water": {
            "name": "智慧流动型",
            "traits": "深思熟虑、善于观察、灵活变通",
            "description": "你的能量倾向于向内流动和沉淀，喜欢深度思考，具有强烈的洞察力。",
        },
    }

    energy_type = energy_types[dominant_element]

    return {
        "basic_info": {
            "name": user_data.get("name", ""),
            "birth_date": f"{birth_year}-{birth_month}-{birth_day}",
            "report_date": None,
            "generated_by": "Basic Algorithm",
        },
        "energy_profile": {
            "type": energy_type["name"],
            "core_traits": energy_type["traits"],
            "description": energy_type["description"],
        },
        "career_guidance": {
            "suitable_paths": ["创意型工作", "分析型工作", "管理型工作"],
            "work_style": "根据个人特质发挥优势",
            "development_suggestions": ["持续学习", "拓展人脉", "发挥优势"],
        },
        "relationship_pattern": {
            "style": "独特的关系互动模式",
            "strengths": ["真诚", "理解", "支持"],
            "challenges": ["需要学习的方面"],
            "growth_direction": "持续成长和改善",
        },
        "personal_growth": {
            "current_issues": [f"关注{topic}相关议题" for topic in selected_topics],
            "action_plan": [
                {
                    "area": "能量管理",
                    "action": "每天预留30分钟独处时间，进行自我觉察",
                    "timeline": "立即开始",
                }
            ],
            "resources": ["推荐书籍", "推荐工具", "推荐实践"],
        },
        "summary": (
            f"你是{energy_type['name']}，具有{energy_type['traits']}的特质。"
            "建议你从认识自己的能量模式开始，逐步建立适合自己的成长路径。"
        ),
        "ai_generated_content": None,
    }
