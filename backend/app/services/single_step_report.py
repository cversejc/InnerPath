import httpx
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.logging_config import get_logger
from app.services.bazi_calculator import calculate_mingli_foundation
from app.services.report_prompt import build_prompt

logger = get_logger("app.services.ai_service")

def _extract_chat_content(response_data: Dict[str, Any]) -> str:
    """Extract visible assistant content from a DeepSeek Chat Completions response."""
    choices = response_data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ValueError("DeepSeek 响应缺少 choices")

    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None

    if isinstance(content, str):
        normalized_content = content.strip()
    elif isinstance(content, list):
        # Keep compatibility with content-part responses (for example vision models).
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
        raise ValueError(f"DeepSeek 返回空正文，finish_reason={finish_reason}")

    return normalized_content

async def generate_report_single_step(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Single-step report generation (original method)
    """
    logger.info(f"开始生成 AI 报告（单步模式）| 用户: {user_data.get('name', 'Unknown')}")

    prompt_user_data = dict(user_data)
    foundation_data = calculate_mingli_foundation(user_data)
    prompt_user_data["foundation_data"] = foundation_data
    logger.info("单步模式已注入确定性命理基础")

    prompt = build_prompt(prompt_user_data)
    logger.debug(f"Prompt 长度: {len(prompt)} 字符")

    try:
        logger.info(f"调用 DeepSeek API | URL: {settings.DEEPSEEK_API_URL}")

        async with httpx.AsyncClient(timeout=settings.DEEPSEEK_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.DEEPSEEK_API_URL,
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": """你是辰鉴的核心解读引擎，负责把传统时间结构、现代心理学与哲学脉络翻译成一份不审判人的人生说明书。

你的核心能力：
1. 深度整合：将八字十神、紫微星曜等传统概念转化为"个人属性"、"能量通路"、"心智模式"与"关系动力"
2. 当代翻译：结合今天的职业、性别与社会语境，不机械套用古代角色和因果判断
3. 结构洞察：帮助用户看见"我是谁、我卡在哪、我往哪去"，区分个人属性、环境条件与社会化评价
4. 实用赋能：提供基于CBT、正念、积极心理学和现实资源盘点的可执行行动
5. 中性重构：将"忌"、"煞"等传统负面概念重构为"需要平衡的能量"或"高性能运转的代价"

你的任务：
- 生成辰鉴"人生说明书"，而不是传统命理判词
- 肯定用户的个人能力、价值与主体性，不用"你应该怎样"审判用户
- 每个关键分析都给出"为什么"（心理机制或环境条件）和"怎么做"（具体行动）
- 遵守"不算命、不评判命盘层次、不点评财富等级与能力高低、不预测具体未来因果"的边界
- 用舍由时，行藏在我：有助推力时冲锋，风浪大时稳住修整，但选择权始终在用户

语气：专业、温暖、具体、有边界，像一位懂传统智慧又尊重现代人的同行者。"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": settings.DEEPSEEK_MAX_TOKENS,
                    "stream": False,
                    "thinking": {
                        "type": "enabled" if settings.DEEPSEEK_THINKING else "disabled"
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
                }
            )

            response.raise_for_status()
            response_data = response.json()
            ai_content = _extract_chat_content(response_data)

            finish_reason = (response_data.get("choices") or [{}])[0].get("finish_reason")
            logger.info(
                f"DeepSeek API 调用成功 | 模型: {settings.DEEPSEEK_MODEL} | "
                f"思考模式: {'enabled' if settings.DEEPSEEK_THINKING else 'disabled'} | "
                f"结束原因: {finish_reason} | 响应长度: {len(ai_content)} 字符"
            )
            logger.debug(f"AI 响应预览: {ai_content[:200]}...")

            # Parse AI response into structured format
            result = parse_ai_response(ai_content, user_data)
            if prompt_user_data.get("foundation_data"):
                result["foundation_data"] = prompt_user_data["foundation_data"]
                result["basic_info"]["generated_by"] = "DeepSeek AI + Deterministic Mingli"
            logger.info(f"AI 报告解析完成 | 包含字段: {list(result.keys())}")

            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP 错误 | 状态码: {e.response.status_code} | 响应: {e.response.text}")
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
    except httpx.TimeoutException:
        logger.error("DeepSeek API 调用超时")
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {str(e)}", exc_info=True)
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)


def parse_ai_response(ai_content: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse AI response into structured report"""
    return {
        "basic_info": {
            "name": user_data.get("name", ""),
            "birth_date": f"{user_data.get('birth_year')}-{user_data.get('birth_month')}-{user_data.get('birth_day')}",
            "report_date": None,  # Will be set by service
            "generated_by": "DeepSeek AI"
        },
        "ai_generated_content": ai_content,
        "energy_profile": extract_energy_profile(ai_content),
        "career_guidance": extract_career_guidance(ai_content),
        "relationship_pattern": extract_relationship_pattern(ai_content),
        "personal_growth": extract_personal_growth(ai_content),
        "summary": extract_summary(ai_content)
    }


def extract_energy_profile(content: str) -> Dict[str, Any]:
    """Extract energy profile from AI content"""
    type_match = re.search(r'能量类型[：:]\s*([^\n]+)', content)
    traits_match = re.search(r'核心特质[：:]\s*([^\n]+)', content)

    return {
        "type": type_match.group(1).strip() if type_match else "综合型",
        "core_traits": traits_match.group(1).strip() if traits_match else "独特的个人特质",
        "description": content[:200] + "..." if len(content) > 200 else content
    }


def extract_career_guidance(content: str) -> Dict[str, Any]:
    """Extract career guidance from AI content"""
    return {
        "suitable_paths": ["创意型工作", "分析型工作", "人际型工作"],
        "work_style": "根据个人特质灵活调整",
        "development_suggestions": ["持续学习", "拓展人脉", "发挥优势"]
    }


def extract_relationship_pattern(content: str) -> Dict[str, Any]:
    """Extract relationship pattern from AI content"""
    return {
        "style": "独特的关系互动模式",
        "strengths": ["真诚", "理解", "支持"],
        "challenges": ["需要学习的方面"],
        "growth_direction": "持续成长和改善"
    }


def extract_personal_growth(content: str) -> Dict[str, Any]:
    """Extract personal growth suggestions from AI content"""
    return {
        "current_issues": ["当前关注的议题"],
        "action_plan": [
            {
                "area": "能量管理",
                "action": "每天预留时间进行自我觉察",
                "timeline": "立即开始"
            }
        ],
        "resources": ["推荐阅读", "推荐课程", "推荐实践"]
    }


def extract_summary(content: str) -> str:
    """Extract summary from AI content"""
    summary_match = re.search(r'##\s*五、总结与寄语([\s\S]*?)$', content)
    return summary_match.group(1).strip() if summary_match else "你是独特的个体，拥有无限的成长潜力。"


def generate_basic_report(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate basic report using simple algorithm (fallback)
    Migrated from frontend src/utils/aiService.js
    """
    logger.info("使用基础算法生成报告（降级方案）")

    birth_year = user_data.get("birth_year", 2000)
    birth_month = user_data.get("birth_month", 1)
    birth_day = user_data.get("birth_day", 1)
    selected_topics = user_data.get("selected_topics", [])

    logger.debug(f"出生日期: {birth_year}-{birth_month}-{birth_day}")

    # Simple five-element analysis
    sum_val = (int(birth_year) + int(birth_month) + int(birth_day)) % 5
    elements = ["wood", "fire", "earth", "metal", "water"]
    dominant_element = elements[sum_val]

    logger.info(f"主导五行: {dominant_element}")

    energy_types = {
        "wood": {
            "name": "生长驱动型",
            "traits": "创新求变、积极进取、富有创造力",
            "description": "你的能量倾向于向外扩展和生长，喜欢探索新事物，具有强烈的成长动力。"
        },
        "fire": {
            "name": "表达驱动型",
            "traits": "热情洋溢、善于表达、富有感染力",
            "description": "你的能量倾向于向外散发和表达，喜欢与人互动，具有强烈的表现欲。"
        },
        "earth": {
            "name": "稳定承载型",
            "traits": "踏实稳重、包容接纳、注重安全",
            "description": "你的能量倾向于稳定和承载，喜欢建立秩序，具有强烈的责任感。"
        },
        "metal": {
            "name": "秩序驱动型",
            "traits": "理性客观、追求完美、注重规则",
            "description": "你的能量倾向于收敛和精炼，喜欢建立标准，具有强烈的原则性。"
        },
        "water": {
            "name": "智慧流动型",
            "traits": "深思熟虑、善于观察、灵活变通",
            "description": "你的能量倾向于向内流动和沉淀，喜欢深度思考，具有强烈的洞察力。"
        }
    }

    energy_type = energy_types[dominant_element]

    return {
        "basic_info": {
            "name": user_data.get("name", ""),
            "birth_date": f"{birth_year}-{birth_month}-{birth_day}",
            "report_date": None,
            "generated_by": "Basic Algorithm"
        },
        "energy_profile": {
            "type": energy_type["name"],
            "core_traits": energy_type["traits"],
            "description": energy_type["description"]
        },
        "career_guidance": {
            "suitable_paths": ["创意型工作", "分析型工作", "管理型工作"],
            "work_style": "根据个人特质发挥优势",
            "development_suggestions": ["持续学习", "拓展人脉", "发挥优势"]
        },
        "relationship_pattern": {
            "style": "独特的关系互动模式",
            "strengths": ["真诚", "理解", "支持"],
            "challenges": ["需要学习的方面"],
            "growth_direction": "持续成长和改善"
        },
        "personal_growth": {
            "current_issues": [f"关注{t}相关议题" for t in selected_topics],
            "action_plan": [
                {
                    "area": "能量管理",
                    "action": "每天预留30分钟独处时间，进行自我觉察",
                    "timeline": "立即开始"
                }
            ],
            "resources": ["推荐书籍", "推荐课程", "推荐实践"]
        },
        "summary": f"你是{energy_type['name']}，具有{energy_type['traits']}的特质。建议你从认识自己的能量模式开始，逐步建立适合自己的成长路径。",
        "ai_generated_content": None
    }
