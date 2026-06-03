import json
from typing import Any, Dict


def build_prompt(user_data: Dict[str, Any]) -> str:
    """Build the AI interpretation prompt from deterministic foundation data."""
    name = user_data.get("name", "")
    gender = user_data.get("gender", "")
    birth_year = user_data.get("birth_year", "")
    birth_month = user_data.get("birth_month", "")
    birth_day = user_data.get("birth_day", "")
    birth_hour = user_data.get("birth_hour")
    birth_minute = user_data.get("birth_minute")
    selected_topics = user_data.get("selected_topics", [])
    additional_info = user_data.get("additional_info", "")
    foundation_data = user_data.get("foundation_data")

    if not foundation_data:
        raise ValueError("缺少确定性命理基础，不能生成AI解读")

    gender_text = "男" if gender == "male" else "女"
    birth_time = f"{birth_hour}时{birth_minute}分" if birth_hour is not None and birth_minute is not None else "时辰未知"

    topic_map = {
        "career": "职业发展",
        "relationship": "亲密关系",
        "family": "家庭议题",
        "self": "自我价值",
        "growth": "个人成长",
        "stress": "压力焦虑",
    }

    topics_text = "、".join([topic_map.get(t, t) for t in selected_topics]) if selected_topics else "全面自我探索"
    additional_section = f"【补充说明】\n{additional_info}\n" if additional_info else ""
    foundation_section = f"""

【确定性命理基础】
{json.dumps(foundation_data, ensure_ascii=False, indent=2)}
"""

    return f"""请为以下用户生成一份深度整合的"成长报告"：

【基本信息】
姓名：{name}
性别：{gender_text}
出生日期：{birth_year}年{birth_month}月{birth_day}日 {birth_time}

【关注议题】
{topics_text}
{foundation_section}

{additional_section}

请按照以下结构生成报告（每个部分都要深度分析，不要泛泛而谈）：

## 一、能量内核（基于八字分析）

**第一步：排出天干地支**
- 根据【确定性命理基础】呈现年柱、月柱、日柱（如果有时辰则呈现时柱）
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

**第一步：呈现紫微命盘**
- 基于【确定性命理基础】标注命宫、财帛宫、事业宫、夫妻宫主星
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
1. 基于上方【确定性命理基础】进行解读，不要重新排盘或改写四柱/宫位
2. 每个分析都要说明"为什么"（心理机制）和"怎么做"（具体行动）
3. 避免"命中注定"等宿命论表述
4. 用"能量"、"模式"、"配置"等中性词汇
5. 整合传统智慧与现代心理学，展现专业深度
6. 语言要像一位既懂命理又懂心理学的导师，专业而温暖"""
