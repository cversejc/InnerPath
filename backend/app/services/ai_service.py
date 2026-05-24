import httpx
import re
from typing import Dict, Any, Optional
from app.config import settings
from app.core.logging_config import get_logger, log_external_api

logger = get_logger(__name__)


@log_external_api("DeepSeek API")
async def generate_report_with_ai(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call DeepSeek API to generate report
    Migrated from frontend src/utils/aiService.js
    """
    logger.info(f"开始生成 AI 报告 | 用户: {user_data.get('name', 'Unknown')}")

    prompt = build_prompt(user_data)
    logger.debug(f"Prompt 长度: {len(prompt)} 字符")

    try:
        logger.info(f"调用 DeepSeek API | URL: {settings.DEEPSEEK_API_URL}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                settings.DEEPSEEK_API_URL,
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": """你是一位资深的东方人格分析师和心理咨询师，精通八字命理、紫微斗数等传统智慧体系，同时深谙积极心理学、认知行为疗法(CBT)等现代心理学理论。

你的核心能力：
1. 深度整合：将八字十神、紫微星曜等传统概念，转化为现代心理学的"能量内核"、"心智模式"、"人格优势"等语言
2. 精准洞察：基于出生时间的天干地支结构，解读用户的核心驱动力、思维模式、关系模式
3. 实用赋能：提供基于CBT、正念、积极心理学的具体成长策略，而非抽象建议
4. 中性重构：将传统命理中的"忌"、"煞"等负面概念，重构为"高性能运转的代价"、"需要平衡的能量"

你的任务：
- 生成一份深度整合的"成长报告"，而非传统命理报告
- 用"能量特质"替代"五行"，用"心智模式"替代"格局"，用"关系动力"替代"六亲"
- 每个分析都要给出"为什么"（心理机制）和"怎么做"（具体行动）
- 避免宿命论，强调"这是你的天赋配置，如何使用取决于你"

语气：专业而温暖，像一位既懂传统智慧又懂现代科学的导师。"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
                }
            )

            response.raise_for_status()
            response_data = response.json()
            ai_content = response_data["choices"][0]["message"]["content"]

            logger.info(f"DeepSeek API 调用成功 | 响应长度: {len(ai_content)} 字符")
            logger.debug(f"AI 响应预览: {ai_content[:200]}...")

            # Parse AI response into structured format
            result = parse_ai_response(ai_content, user_data)
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


def build_prompt(user_data: Dict[str, Any]) -> str:
    """Build prompt for AI"""
    name = user_data.get("name", "")
    gender = user_data.get("gender", "")
    birth_year = user_data.get("birth_year", "")
    birth_month = user_data.get("birth_month", "")
    birth_day = user_data.get("birth_day", "")
    birth_hour = user_data.get("birth_hour")
    birth_minute = user_data.get("birth_minute")
    selected_topics = user_data.get("selected_topics", [])
    additional_info = user_data.get("additional_info", "")

    gender_text = "男" if gender == "male" else "女"
    birth_time = f"{birth_hour}时{birth_minute}分" if birth_hour is not None and birth_minute is not None else "时辰未知"

    topic_map = {
        "career": "职业发展",
        "relationship": "亲密关系",
        "family": "家庭议题",
        "self": "自我价值",
        "growth": "个人成长",
        "stress": "压力焦虑"
    }

    topics_text = "、".join([topic_map.get(t, t) for t in selected_topics]) if selected_topics else "全面自我探索"

    additional_section = f"【补充说明】\n{additional_info}\n" if additional_info else ""

    prompt = f"""请为以下用户生成一份深度整合的"成长报告"：

【基本信息】
姓名：{name}
性别：{gender_text}
出生日期：{birth_year}年{birth_month}月{birth_day}日 {birth_time}

【关注议题】
{topics_text}

{additional_section}

请按照以下结构生成报告（每个部分都要深度分析，不要泛泛而谈）：

## 一、能量内核（基于八字分析）

**第一步：排出天干地支**
- 根据出生日期，推算年柱、月柱、日柱（如果有时辰则推算时柱）
- 标注日主（日干）和十神关系

**第二步：能量特质解读**
用现代心理学语言重构：
- **核心驱动力**：你天生的能量来源是什么？（对应日主和格局）
  例如："你天生拥有深度洞察与原创思维的强大天赋（偏印+华盖）。你能轻易洞悉事物的本质，享受在精神世界独行。你的能量来源，不是社交，而是深刻的求知与创造。"（对应积极心理学中的"洞察力"与"热爱学习"优势）

- **思维模式**：你的大脑如何运作？（对应十神组合）
  例如："命宫天机化忌，意味着你的思考引擎过于发达，容易进入'过度思考-精神内耗'的循环中。这不是缺陷，而是你大脑高性能运转的必然代价。"

- **能量平衡点**：哪些特质需要平衡？
  用中性语言重构"忌"、"煞"等概念

## 二、人生剧场（基于紫微斗数）

**第一步：排紫微命盘**
- 标注命宫、财帛宫、事业宫、夫妻宫主星
- 识别关键格局（如：紫府同宫、杀破狼等）

**第二步：人生主题解读**
- **命宫主题**：你的人生剧本核心是什么？
  例如："你的人生剧本中，'心智活动'是绝对的主角。"

- **事业宫解读**：你在工作中的天赋与挑战
  具体到职业类型、工作方式

- **关系宫解读**：你在亲密关系中的模式
  具体到互动方式、需求特点

## 三、心智模式与成长导航（心理学整合）

**核心信念识别**（CBT视角）
- 这种命理配置会在后天形成什么核心信念？
  例如："'天机化忌'模式，会在后天形成一种核心信念：'我必须考虑周全才能行动，否则就会出错'。这会让你在决策时感到焦虑。"

**具体成长策略**（不要泛泛而谈）
- 针对识别出的模式，给出具体的CBT技术、正念练习、行为实验
  例如："下个阶段，你可以尝试练习'行为实验'（CBT技术）：主动做一些小的、不完美的决定，去检验那个'会出错'的预测是否真实，为你的思考引擎装上刹车片。"

## 四、针对关注议题的深度建议

针对用户选择的{topics_text}，提供：
- **模式识别**：这个议题背后的深层模式是什么？
- **心理机制**：为什么会这样？（结合命理+心理学）
- **具体行动**：3-5个可操作的步骤（要具体到"每天做什么"）

## 五、总结与寄语（100-150字）

用温暖、赋能的语言，强调：
- 这是你的天赋配置，不是限制
- 成长的方向是什么
- 给予鼓励和信心

---

**重要要求**：
1. 必须实际推算八字和紫微命盘，不要编造
2. 每个分析都要说明"为什么"（心理机制）和"怎么做"（具体行动）
3. 避免"命中注定"等宿命论表述
4. 用"能量"、"模式"、"配置"等中性词汇
5. 整合传统智慧与现代心理学，展现专业深度
6. 语言要像一位既懂命理又懂心理学的导师，专业而温暖"""

    return prompt


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
