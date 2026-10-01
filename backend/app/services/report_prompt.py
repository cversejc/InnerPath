import json
from typing import Any, Dict

from app.services.intake_prompt_context import (
    context_for_prompt,
    profile_context_for_prompt,
)


SYSTEM_PROMPT = """你是辰鉴的核心解读引擎，负责把传统时间结构、现代心理学与哲学脉络翻译成一份不审判人的人生说明书。

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


def build_prompt(user_data: Dict[str, Any]) -> str:
    """Build the chenvis life-manual prompt from deterministic foundation data."""
    name = user_data.get("name", "")
    gender = user_data.get("gender", "")
    birth_year = user_data.get("birth_year", "")
    birth_month = user_data.get("birth_month", "")
    birth_day = user_data.get("birth_day", "")
    birth_hour = user_data.get("birth_hour")
    birth_minute = user_data.get("birth_minute")
    calendar_type = user_data.get("calendar_type", "solar")
    birth_time_precision = user_data.get("birth_time_precision", "unknown")
    selected_topics = user_data.get("selected_topics", [])
    additional_info = user_data.get("additional_info", "")
    foundation_data = user_data.get("foundation_data")
    context = user_data.get("context") or {
        "focus_topics": selected_topics,
        "additional_info": additional_info,
    }

    if not foundation_data:
        raise ValueError("缺少确定性命理基础，不能生成AI解读")

    gender_text = "男" if gender == "male" else "女"
    birth_time = (
        f"{birth_hour}时{birth_minute}分"
        if birth_hour is not None and birth_minute is not None
        else "时辰未知"
    )
    calendar_text = "农历" if calendar_type == "lunar" else "公历"
    precision_text = {
        "unknown": "未知",
        "approximate": "大概时间",
        "exact": "精确时间",
    }.get(birth_time_precision, birth_time_precision or "未知")

    topic_map = {
        "career": "职业发展",
        "relationship": "亲密关系",
        "family": "家庭议题",
        "finance": "财务规划",
        "health": "身心健康",
        "social": "人际关系",
        "children": "子女教育",
        "self": "自我价值",
        "growth": "个人成长",
        "stress": "压力焦虑",
    }

    topics_text = (
        "、".join([topic_map.get(t, t) for t in selected_topics])
        if selected_topics
        else "全面自我探索"
    )
    additional_section = f"【补充说明】\n{additional_info}\n" if additional_info else ""
    context_section = context_for_prompt(context)
    profile_section = profile_context_for_prompt(user_data)
    foundation_section = f"""

【确定性命理基础】
{json.dumps(foundation_data, ensure_ascii=False, indent=2)}
"""

    return f"""请为以下用户生成一份「辰鉴·人生说明书」。

辰鉴的核心是“星辰引路，镜子照见”：借助时间结构观察个人属性与环境时序，再用心理学和哲学语言帮助用户理解自己、做出选择。请把用户当作有主体性、有能力把生活过好的人，而不是等待被判断的人。

【基本信息】
姓名：{name}
性别：{gender_text}
出生日期：{birth_year}年{birth_month}月{birth_day}日（{calendar_text}）{birth_time}
出生时间准确度：{precision_text}

【可复用个人背景】
{profile_section or "暂无补充背景"}

【关注议题】
{topics_text}
【本次申请情境】
{context_section or "暂无补充情境"}
{foundation_section}

{additional_section}

请按照以下结构输出，标题请保留：

## 一、我是谁 · 性格密码与能量通路

### 1. 性格密码
- 基于【确定性命理基础】描述用户的核心驱动力、思维方式、表达方式与关系倾向。
- 具体指出天赋点，以及天赋过度使用、用错或环境不适配时会出现的干扰。
- 把“忌”“煞”等传统负面词汇翻译成中性的能量平衡点，不进行人格贬低。

### 2. 能量通路
- 说明什么类型的事情、关系和环境可能帮助用户充电，什么会耗电。
- 解释如何让个人属性与现实环境更好适配。

### 3. 关系模式
- 如果与用户议题相关，说明其在亲密关系、家庭或职场中的互动模式。
- 给出理解差异、保持边界和进行有效沟通的方向，而不是给他人贴标签。

## 二、我卡在哪 · 核心矛盾与人生重复模式

### 1. 当前核心矛盾
- 结合用户的具体处境，说明当下最值得被看见的矛盾，不要泛泛谈整个人生。
- 优先区分“个人属性”“环境条件”和“社会化评价”，避免把结构性处境归咎于个人。

### 2. 卡点全景图
请依次回应：
- 你在“想要”和“恐惧”之间如何反复横跳？
- 你的人生重复模式是什么？
- 你的“内在小孩”可能在保护什么、呼唤什么？
- 哪一种“人生谎言”正在让你放弃自己的判断？

## 三、我往哪去 · 破局点与下一步行动

### 1. 下周就可以做的 3 件事
- 给出三个小而具体的行动，每项包含动作、频率或完成标准。
- 行动要尊重用户当前资源，不使用“你应该”“你必须”式审判语气。

### 2. 未来 6—12 个月的能力建设
- 给出 2—4 个可积累的能力或环境建设方向，并说明为什么与用户的个人属性相适配。

### 3. 决策节奏
- 说明什么情况下适合推进、什么情况下适合观察或修整。
- 使用“用舍由时，行藏在我”的原则：有助推力时冲锋，风浪大时稳住修整，但最终选择权在用户。

## 四、针对关注议题的回应

针对用户选择的{topics_text}，分别说明：
- 具体情境中的结构与旧循环
- 个人属性、环境条件与社会期待如何交织
- 一至三个可以验证的行动或对话实验

## 五、总结与寄语

用 100—150 字总结，肯定用户已经拥有的能力与价值，给出希望与方向，但不要预测具体未来，不制造因果恐惧。

---

**重要要求**：
1. 必须基于上方【确定性命理基础】进行解读，不要重新排盘或改写四柱/宫位。
2. 传统工具只用于观察个人属性与时间节律，不把它写成宿命、财富等级、能力高低或具体因果预测。
3. 不评判用户“不够努力”“不够成熟”或“走错了”；把所谓错误解构为阶段、环境和可调整的能量堵点。
4. 允许使用当代语境解释传统符号：例如事业、创意、破局和新思维，不机械套用古代社会角色。
5. 每个关键判断都要说明“为什么”，每个建议都要说明“怎么做”。
6. 不提供医疗诊断、危机干预或法律/财务专业结论；保持专业、温暖、具体、有边界。"""
