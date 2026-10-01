import json
from typing import Any, Dict

from app.services.intake_prompt_context import (
    context_for_prompt,
    profile_context_for_prompt,
)


class MultiStepReportPrompts:
    def _build_step2_prompt(
        self, foundation_data: Dict[str, Any], user_data: Dict[str, Any]
    ) -> str:
        """Build Step 2 prompt: Energy profile analysis"""
        gender = user_data.get("gender", "")
        selected_topics = user_data.get("selected_topics", [])

        gender_text = "男" if gender == "male" else "女"

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
            "stress": "压力焦虑"
        }
        topics_text = "、".join([topic_map.get(t, t) for t in selected_topics]) if selected_topics else "全面自我探索"
        context_text = context_for_prompt(user_data.get("context") or {"focus_topics": selected_topics})
        profile_text = profile_context_for_prompt(user_data.get("profile") or user_data)

        # Format foundation data for display
        foundation_str = json.dumps(foundation_data, ensure_ascii=False, indent=2)

        return f"""你是辰鉴 fi 端的深度分析师，整合东方智慧、现代心理学与当代哲学。

你的任务不是给用户下命理结论，而是用时间结构作为观察个人属性的镜子，帮助用户理解“我是谁”。

【命理基础】
{foundation_str}

【性别】{gender_text}

【可复用个人背景】
{profile_text or "暂无补充背景"}

【用户关注领域】{topics_text}（这些是用户当前关注的生命领域，解读时需考虑这些背景）

【本次申请情境】
{context_text or "暂无补充情境"}

请提供：

        ## 一、我是谁 · 性格密码与能量通路

        #### 1. 核心驱动力与天赋点
   - 基于日主和格局，此人的天然能量来源是什么？
   - 用现代心理学语言描述（对应积极心理学的优势）
           - 明确指出个人属性的优势，以及过度使用或环境不适配时出现的干扰。

        #### 2. 思维模式与能量通路
   - 基于十神组合和紫微命宫，此人的思维如何运作？
   - 指出高性能特质及其代价
           - 说明什么事情充电、什么事情耗电，并把高性能特质的代价说清楚。

        #### 3. 关系模式
           - 说明在亲密关系、家庭或职场中的互动方式与边界需要。

        ## 二、当下的个人坐标

        基于确定性基础与用户关注领域：

        #### 1. 个人属性与现实环境
           - 区分个人属性、环境条件和社会化评价。

        #### 2. 事业与选择条件
           - 工作中的天赋与挑战，以及更适合的工作方式；不要给职业等级或确定性预测。

        #### 3. 当前阶段的时序提示
           - 说明当下更适合推进、观察还是修整，并强调选择权在用户。

语言要求：
        - 专业而温暖，像一位既懂传统智慧又懂心理学的同行者
        - 用"能量"、"模式"、"配置"等中性词汇
        - 避免宿命论、等级评价与“你应该怎样”的审判语气
        - 使用当代语境翻译传统符号，不机械套用古代性别与社会角色
        - 直接输出内容，不要在标题中包含字数要求
- 总字数：1000-1200字"""

    def _build_step3_prompt(
        self, foundation_data: Dict[str, Any], energy_profile: str, user_data: Dict[str, Any]
    ) -> str:
        """Build Step 3 prompt: Topic-specific analysis"""
        selected_topics = user_data.get("selected_topics", [])
        additional_info = user_data.get("additional_info", "")
        context_text = context_for_prompt(user_data.get("context") or {
            "focus_topics": selected_topics,
            "additional_info": additional_info,
        })
        profile_text = profile_context_for_prompt(user_data.get("profile") or user_data)

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
            "stress": "压力焦虑"
        }

        topics_list = [topic_map.get(t, t) for t in selected_topics] if selected_topics else []
        topics_text = "、".join(topics_list)

        foundation_str = json.dumps(foundation_data, ensure_ascii=False, indent=2)

        additional_section = f"""
【用户补充说明】
{additional_info}
""" if additional_info else ""

        # Build topic-specific sections
        topic_sections = ""
        for topic in topics_list:
            topic_sections += f"""
---

## 针对【{topic}】的深度分析

### 1. 模式识别
- 基于此人的命理配置和能量特质，在{topic}领域会呈现什么深层模式？
- 结合用户的补充说明，识别具体情境中的模式

### 2. 心理机制与环境条件
- 为什么会形成这种模式？（个人属性 + 心理学解释）
- 哪些是个人可以调整的，哪些是环境或社会结构带来的？

### 3. 具体行动方案
提供 3-5 个可操作的步骤：
- 必须具体到"每天/每周做什么"
- 整合 CBT 技术、正念练习、行为实验与现实资源盘点
- 针对用户补充说明中的具体情境给出建议
- 避免“你应该”“你必须”等审判语气，给出可选择的路径

### 4. 成长资源
- 推荐 2-3 个具体资源（书籍、工具、实践方法）
- 必须与此议题和用户情境相关

"""

        return f"""你是辰鉴 te 端的行动与决策陪伴者，整合东方智慧、现代心理学（CBT、正念、积极心理学）与现实处境。

你的任务不是替用户做社会化判断，也不是预测未来，而是把 fi 端的人生说明书翻译成当下能使用的选择支持。

【背景信息】
命理基础：
{foundation_str}

能量特质：
{energy_profile}

【可复用个人背景】
{profile_text or "暂无补充背景"}

【用户选择的关注议题】
{topics_text}
【本次申请情境】
{context_text or "暂无补充情境"}
{additional_section}

重要：用户专门选择了这些议题，说明这些是他们当前最关心的领域。你的分析必须直接回应这些议题，并结合补充说明中的具体情境。请先肯定用户已有的能力与处境，再讨论可以调整的行动。

请针对每个选择的议题，提供深度分析：

{topic_sections}

---

## 总结与寄语

整合所有分析，给出：
- 核心信念识别（CBT 视角）
- 成长的核心方向
- 温暖、赋能的鼓励

强调：这是你的天赋配置，不是限制；用舍由时，行藏在我。

---

语言要求：
- 必须直接回应用户选择的议题和补充说明
- 每个议题的分析要有明显的个性化特征
- 避免泛泛而谈的通用建议
- 专业、温暖、可操作，保护用户主体性
- 不点评财富等级、能力高低，不预测具体未来走向或因果
- 直接输出内容，不要在标题中包含字数要求或格式说明"""

