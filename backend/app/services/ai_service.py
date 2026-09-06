import httpx
import re
import json
import os
from typing import Dict, Any, Optional, List
from app.config import settings
from app.core.logging_config import get_logger, log_external_api
from app.services.bazi_calculator import calculate_mingli_foundation
from app.services.report_prompt import build_prompt

logger = get_logger(__name__)


class MultiStepReportGenerator:
    """Multi-step AI report generation with progressive context building"""

    def __init__(self):
        self.api_url = settings.DEEPSEEK_API_URL
        self.api_key = settings.DEEPSEEK_API_KEY
        self.model = settings.DEEPSEEK_MODEL

    async def generate_report(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration method for multi-step report generation"""
        logger.info(f"开始多步报告生成 | 用户: {user_data.get('name', 'Unknown')}")

        try:
            # Step 1: Foundation calculation
            logger.info("Step 1: 建立先天坐标...")
            foundation_data = await self._step1_foundation(user_data)
            logger.info(f"Step 1 完成 | 基础数据: {json.dumps(foundation_data, ensure_ascii=False)[:100]}...")

            # Step 2: Energy profile analysis
            logger.info("Step 2: 解读能量特质...")
            energy_profile = await self._step2_energy_profile(foundation_data, user_data)
            logger.info(f"Step 2 完成 | 能量解读长度: {len(energy_profile)} 字符")

            # Step 3: Topic-specific analysis
            logger.info("Step 3: 分析关注议题...")
            topic_analysis = await self._step3_topic_analysis(
                foundation_data, energy_profile, user_data
            )
            logger.info(f"Step 3 完成 | 议题分析长度: {len(topic_analysis)} 字符")

            # Assemble final report
            logger.info("组装最终报告...")
            report = self._assemble_report(
                foundation_data, energy_profile, topic_analysis, user_data
            )
            logger.info("多步报告生成完成")

            return report

        except Exception as e:
            logger.error(f"多步报告生成失败: {str(e)}", exc_info=True)
            logger.warning("降级到单步方法")
            raise

    async def _step1_foundation(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: Calculate astrological foundations using deterministic calculation"""
        logger.info("使用确定性算法建立个人先天坐标")
        result = calculate_mingli_foundation(user_data)
        logger.info(f"先天坐标建立完成 | 日主: {result['bazi']['day_master']} | 方法: 确定性计算")
        return result

    async def _step2_energy_profile(
        self, foundation_data: Dict[str, Any], user_data: Dict[str, Any]
    ) -> str:
        """Step 2: Analyze energy profile"""
        prompt = self._build_step2_prompt(foundation_data, user_data)
        return await self._call_ai(prompt, temperature=0.7, max_tokens=2000)

    async def _step3_topic_analysis(
        self, foundation_data: Dict[str, Any], energy_profile: str, user_data: Dict[str, Any]
    ) -> str:
        """Step 3: Generate topic-specific analysis"""
        prompt = self._build_step3_prompt(foundation_data, energy_profile, user_data)

        # Adjust max_tokens based on number of topics
        selected_topics = user_data.get("selected_topics", [])
        max_tokens = 2000 + (len(selected_topics) * 500)  # ~500 tokens per topic
        max_tokens = min(max_tokens, 4000)  # Cap at 4000

        return await self._call_ai(prompt, temperature=0.7, max_tokens=max_tokens)

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
            "self": "自我价值",
            "growth": "个人成长",
            "stress": "压力焦虑"
        }
        topics_text = "、".join([topic_map.get(t, t) for t in selected_topics]) if selected_topics else "全面自我探索"

        # Format foundation data for display
        foundation_str = json.dumps(foundation_data, ensure_ascii=False, indent=2)

        return f"""你是辰鉴 fi 端的深度分析师，整合东方智慧、现代心理学与当代哲学。

你的任务不是给用户下命理结论，而是用时间结构作为观察个人属性的镜子，帮助用户理解“我是谁”。

【命理基础】
{foundation_str}

【性别】{gender_text}

【用户关注领域】{topics_text}（这些是用户当前关注的生命领域，解读时需考虑这些背景）

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

        topic_map = {
            "career": "职业发展",
            "relationship": "亲密关系",
            "family": "家庭议题",
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
- 推荐 2-3 个具体资源（书籍、课程、实践方法）
- 必须与此议题和用户情境相关

"""

        return f"""你是辰鉴 te 端的行动与决策陪伴者，整合东方智慧、现代心理学（CBT、正念、积极心理学）与现实处境。

你的任务不是替用户做社会化判断，也不是预测未来，而是把 fi 端的人生说明书翻译成当下能使用的选择支持。

【背景信息】
命理基础：
{foundation_str}

能量特质：
{energy_profile}

【用户选择的关注议题】
{topics_text}
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

    async def _call_ai(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000
    ) -> str:
        """Call DeepSeek API with given prompt"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )

            response.raise_for_status()
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]

    def _assemble_report(
        self,
        foundation_data: Dict[str, Any],
        energy_profile: str,
        topic_analysis: str,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assemble final report from all steps"""

        # Parse and structure the content for better display
        structured_content = self._parse_structured_content(
            foundation_data, energy_profile, topic_analysis
        )

        logger.info(f"结构化内容解析完成 | 章节数: {len(structured_content)}")
        logger.debug(f"结构化内容: {json.dumps(structured_content, ensure_ascii=False)[:500]}...")

        # Format foundation data as readable Markdown
        foundation_markdown = self._format_foundation_as_markdown(foundation_data)

        # Combine all AI-generated content (pure Markdown)
        full_content = f"""{foundation_markdown}

---

{energy_profile}

{topic_analysis}
"""

        return {
            "basic_info": {
                "name": user_data.get("name", ""),
                "birth_date": f"{user_data.get('birth_year')}-{user_data.get('birth_month')}-{user_data.get('birth_day')}",
                "report_date": None,
                "generated_by": "DeepSeek AI (Multi-Step)"
            },
            "ai_generated_content": full_content,
            "structured_sections": structured_content,  # New: structured sections for UI
            "energy_profile": self._extract_energy_profile(energy_profile),
            "career_guidance": self._extract_career_guidance(topic_analysis),
            "relationship_pattern": self._extract_relationship_pattern(topic_analysis),
            "personal_growth": self._extract_personal_growth(topic_analysis, user_data),
            "summary": self._extract_summary(topic_analysis)
        }

    def _format_foundation_as_markdown(self, foundation_data: Dict[str, Any]) -> str:
        """Format foundation data (bazi, ziwei) as readable Markdown"""

        markdown = "## 命理基础\n\n"

        # Format Bazi (八字)
        if "bazi" in foundation_data:
            bazi = foundation_data["bazi"]
            markdown += "### 八字四柱\n\n"

            # Year pillar
            year = bazi.get("year", {})
            ten_god_year = f"（{year.get('ten_god', '')}）" if year.get('ten_god') else ""
            markdown += f"**年柱：** {year.get('stem', '')}{year.get('branch', '')}{ten_god_year}\n\n"

            # Month pillar
            month = bazi.get("month", {})
            ten_god_month = f"（{month.get('ten_god', '')}）" if month.get('ten_god') else ""
            markdown += f"**月柱：** {month.get('stem', '')}{month.get('branch', '')}{ten_god_month}\n\n"

            # Day pillar
            day = bazi.get("day", {})
            markdown += f"**日柱：** {day.get('stem', '')}{day.get('branch', '')}\n\n"

            # Hour pillar
            hour = bazi.get("hour", {})
            ten_god_hour = f"（{hour.get('ten_god', '')}）" if hour.get('ten_god') else ""
            markdown += f"**时柱：** {hour.get('stem', '')}{hour.get('branch', '')}{ten_god_hour}\n\n"

            markdown += f"**日主：** {bazi.get('day_master', '')}\n\n"

        # Format Ziwei (紫微斗数)
        if "ziwei" in foundation_data:
            ziwei = foundation_data["ziwei"]
            markdown += "### 紫微斗数\n\n"

            # Life palace
            if "life_palace" in ziwei:
                life = ziwei["life_palace"]
                main_stars = "、".join(life.get("main_stars", []))
                markdown += f"**命宫：** {main_stars}\n\n"
                aux_stars = life.get("aux_stars", [])
                if aux_stars:
                    aux_stars_text = "、".join(aux_stars)
                    markdown += f"- 辅星：{aux_stars_text}\n\n"

            # Career palace
            if "career_palace" in ziwei:
                career = ziwei["career_palace"]
                main_stars = "、".join(career.get("main_stars", []))
                markdown += f"**事业宫：** {main_stars}\n\n"

            # Wealth palace
            if "wealth_palace" in ziwei:
                wealth = ziwei["wealth_palace"]
                main_stars = "、".join(wealth.get("main_stars", []))
                markdown += f"**财帛宫：** {main_stars}\n\n"

            # Relationship palace
            if "relationship_palace" in ziwei:
                relationship = ziwei["relationship_palace"]
                main_stars = "、".join(relationship.get("main_stars", []))
                markdown += f"**夫妻宫：** {main_stars}\n\n"

            # Patterns
            if "patterns" in ziwei and ziwei["patterns"]:
                patterns = "、".join(ziwei["patterns"])
                markdown += f"**格局：** {patterns}\n\n"

        return markdown

    def _parse_structured_content(
        self,
        foundation_data: Dict[str, Any],
        energy_profile: str,
        topic_analysis: str
    ) -> Dict[str, Any]:
        """Parse content into structured sections for better UI display"""

        sections = {}

        # Parse foundation data
        sections["foundation"] = {
            "title": "命理基础",
            "type": "foundation",
            "data": foundation_data
        }

        # Parse energy profile sections
        sections["energy"] = self._parse_energy_sections(energy_profile)

        # Parse topic-specific sections
        sections["topics"] = self._parse_topic_sections(topic_analysis)

        # Parse summary
        sections["summary"] = self._parse_summary_section(topic_analysis)

        return sections

    def _parse_energy_sections(self, content: str) -> Dict[str, Any]:
        """Parse energy profile into structured sections"""

        logger.debug(f"解析能量章节，内容长度: {len(content)}")
        logger.debug(f"能量章节内容预览: {content[:500]}")

        sections = {
            "title": "能量特质解读",
            "type": "energy",
            "subsections": []
        }

        # Extract core drive - 更灵活的匹配，支持多种格式
        # 格式1: **核心驱动力**：内容
        # 格式2: 1. **核心驱动力**内容
        # 格式3: **核心驱动力** 内容
        core_drive_patterns = [
            r'\*\*核心驱动力\*\*[：:](.*?)(?=\*\*|##|\d+\.|$)',
            r'\d+\.\s*\*\*核心驱动力\*\*(.*?)(?=\*\*|##|\d+\.|$)',
            r'\*\*核心驱动力\*\*\s+(.*?)(?=\*\*|##|\d+\.|$)'
        ]

        for pattern in core_drive_patterns:
            core_drive_match = re.search(pattern, content, re.DOTALL)
            if core_drive_match:
                sections["subsections"].append({
                    "title": "核心驱动力",
                    "icon": "⚡",
                    "content": core_drive_match.group(1).strip()
                })
                logger.debug("找到核心驱动力章节")
                break

        # Extract thinking pattern
        thinking_patterns = [
            r'\*\*思维模式\*\*[：:](.*?)(?=\*\*|##|\d+\.|$)',
            r'\d+\.\s*\*\*思维模式\*\*(.*?)(?=\*\*|##|\d+\.|$)',
            r'\*\*思维模式\*\*\s+(.*?)(?=\*\*|##|\d+\.|$)'
        ]

        for pattern in thinking_patterns:
            thinking_match = re.search(pattern, content, re.DOTALL)
            if thinking_match:
                sections["subsections"].append({
                    "title": "思维模式",
                    "icon": "🧠",
                    "content": thinking_match.group(1).strip()
                })
                logger.debug("找到思维模式章节")
                break

        # Extract energy balance
        balance_patterns = [
            r'\*\*能量平衡点\*\*[：:](.*?)(?=\*\*|##|\d+\.|$)',
            r'\d+\.\s*\*\*能量平衡点\*\*(.*?)(?=\*\*|##|\d+\.|$)',
            r'\*\*能量平衡点\*\*\s+(.*?)(?=\*\*|##|\d+\.|$)'
        ]

        for pattern in balance_patterns:
            balance_match = re.search(pattern, content, re.DOTALL)
            if balance_match:
                sections["subsections"].append({
                    "title": "能量平衡点",
                    "icon": "⚖️",
                    "content": balance_match.group(1).strip()
                })
                logger.debug("找到能量平衡点章节")
                break

        # Extract life theme sections
        life_theme_match = re.search(r'## 二、人生主题(.*?)(?=##|$)', content, re.DOTALL)
        if life_theme_match:
            theme_content = life_theme_match.group(1)
            logger.debug("找到人生主题章节")

            # Life palace theme
            palace_patterns = [
                r'\*\*命宫主题\*\*[：:](.*?)(?=\*\*|##|\d+\.|$)',
                r'\d+\.\s*\*\*命宫主题\*\*(.*?)(?=\*\*|##|\d+\.|$)',
                r'\*\*命宫主题\*\*\s+(.*?)(?=\*\*|##|\d+\.|$)'
            ]

            for pattern in palace_patterns:
                palace_match = re.search(pattern, theme_content, re.DOTALL)
                if palace_match:
                    sections["subsections"].append({
                        "title": "命宫主题",
                        "icon": "🎭",
                        "content": palace_match.group(1).strip()
                    })
                    break

            # Career traits
            career_patterns = [
                r'\*\*事业特质\*\*[：:](.*?)(?=\*\*|##|\d+\.|$)',
                r'\d+\.\s*\*\*事业特质\*\*(.*?)(?=\*\*|##|\d+\.|$)',
                r'\*\*事业特质\*\*\s+(.*?)(?=\*\*|##|\d+\.|$)'
            ]

            for pattern in career_patterns:
                career_match = re.search(pattern, theme_content, re.DOTALL)
                if career_match:
                    sections["subsections"].append({
                        "title": "事业特质",
                        "icon": "💼",
                        "content": career_match.group(1).strip()
                    })
                    break

            # Relationship pattern
            relation_patterns = [
                r'\*\*关系模式\*\*[：:](.*?)(?=\*\*|##|\d+\.|$)',
                r'\d+\.\s*\*\*关系模式\*\*(.*?)(?=\*\*|##|\d+\.|$)',
                r'\*\*关系模式\*\*\s+(.*?)(?=\*\*|##|\d+\.|$)'
            ]

            for pattern in relation_patterns:
                relation_match = re.search(pattern, theme_content, re.DOTALL)
                if relation_match:
                    sections["subsections"].append({
                        "title": "关系模式",
                        "icon": "💕",
                        "content": relation_match.group(1).strip()
                    })
                    break

        logger.info(f"能量章节解析完成，子章节数: {len(sections['subsections'])}")

        # 如果没有找到任何子章节，将整个内容作为一个章节
        if len(sections['subsections']) == 0:
            logger.warning("未找到任何能量子章节，使用完整内容")
            sections["subsections"].append({
                "title": "能量特质分析",
                "icon": "✨",
                "content": content
            })

        return sections

    def _parse_topic_sections(self, content: str) -> List[Dict[str, Any]]:
        """Parse topic-specific analysis into structured sections"""

        logger.debug(f"解析议题章节，内容长度: {len(content)}")
        logger.debug(f"议题章节内容预览: {content[:500]}")

        topics = []

        # Find all topic sections
        topic_pattern = r'## 针对【(.+?)】的深度分析(.*?)(?=## 针对|## 总结|$)'
        topic_matches = re.finditer(topic_pattern, content, re.DOTALL)

        topic_icons = {
            "职业发展": "💼",
            "亲密关系": "💕",
            "家庭议题": "🏠",
            "自我价值": "✨",
            "个人成长": "🌱",
            "压力焦虑": "🧘"
        }

        for match in topic_matches:
            topic_name = match.group(1)
            topic_content = match.group(2)

            logger.debug(f"找到议题: {topic_name}, 内容长度: {len(topic_content)}")

            topic_section = {
                "title": topic_name,
                "icon": topic_icons.get(topic_name, "📌"),
                "type": "topic",
                "subsections": []
            }

            # Extract pattern recognition - 支持多种格式
            pattern_patterns = [
                r'### 1\.\s*模式识别[：:](.*?)(?=###|$)',
                r'### 1\.\s*模式识别\s+(.*?)(?=###|$)',
                r'\*\*模式识别\*\*[：:](.*?)(?=\*\*|###|$)'
            ]

            for pattern in pattern_patterns:
                pattern_match = re.search(pattern, topic_content, re.DOTALL)
                if pattern_match:
                    topic_section["subsections"].append({
                        "title": "模式识别",
                        "content": pattern_match.group(1).strip()
                    })
                    logger.debug(f"找到 {topic_name} 的模式识别")
                    break

            # Extract psychological mechanism
            mechanism_patterns = [
                r'### 2\.\s*心理机制[：:](.*?)(?=###|$)',
                r'### 2\.\s*心理机制\s+(.*?)(?=###|$)',
                r'\*\*心理机制\*\*[：:](.*?)(?=\*\*|###|$)'
            ]

            for pattern in mechanism_patterns:
                mechanism_match = re.search(pattern, topic_content, re.DOTALL)
                if mechanism_match:
                    topic_section["subsections"].append({
                        "title": "心理机制",
                        "content": mechanism_match.group(1).strip()
                    })
                    logger.debug(f"找到 {topic_name} 的心理机制")
                    break

            # Extract action plan
            action_patterns = [
                r'### 3\.\s*具体行动方案[：:](.*?)(?=###|$)',
                r'### 3\.\s*具体行动方案\s+(.*?)(?=###|$)',
                r'\*\*具体行动方案\*\*[：:](.*?)(?=\*\*|###|$)'
            ]

            for pattern in action_patterns:
                action_match = re.search(pattern, topic_content, re.DOTALL)
                if action_match:
                    action_content = action_match.group(1).strip()
                    # Parse action items
                    actions = self._parse_action_items(action_content)
                    topic_section["subsections"].append({
                        "title": "具体行动方案",
                        "content": action_content,
                        "actions": actions
                    })
                    logger.debug(f"找到 {topic_name} 的具体行动方案，行动项数: {len(actions)}")
                    break

            # Extract resources
            resource_patterns = [
                r'### 4\.\s*成长资源[：:](.*?)(?=###|$)',
                r'### 4\.\s*成长资源\s+(.*?)(?=###|$)',
                r'\*\*成长资源\*\*[：:](.*?)(?=\*\*|###|$)'
            ]

            for pattern in resource_patterns:
                resource_match = re.search(pattern, topic_content, re.DOTALL)
                if resource_match:
                    topic_section["subsections"].append({
                        "title": "成长资源",
                        "content": resource_match.group(1).strip()
                    })
                    logger.debug(f"找到 {topic_name} 的成长资源")
                    break

            # 如果没有找到任何子章节，将整个内容作为一个章节
            if len(topic_section["subsections"]) == 0:
                logger.warning(f"议题 {topic_name} 未找到任何子章节，使用完整内容")
                topic_section["subsections"].append({
                    "title": "分析内容",
                    "content": topic_content.strip()
                })

            logger.debug(f"议题 {topic_name} 解析完成，子章节数: {len(topic_section['subsections'])}")
            topics.append(topic_section)

        logger.info(f"议题章节解析完成，议题数: {len(topics)}")
        return topics

    def _parse_action_items(self, content: str) -> List[Dict[str, str]]:
        """Parse action items from content"""
        actions = []

        # Look for bullet points or numbered items
        action_pattern = r'[*\-•]\s*[""""]?(.+?)[""""]?(?:\n|$)'
        matches = re.finditer(action_pattern, content)

        for match in matches:
            action_text = match.group(1).strip()
            if len(action_text) > 10:  # Filter out very short items
                actions.append({
                    "text": action_text,
                    "completed": False
                })

        return actions[:5]  # Limit to 5 actions

    def _parse_summary_section(self, content: str) -> Dict[str, Any]:
        """Parse summary section"""

        logger.debug(f"解析总结章节，内容长度: {len(content)}")

        summary_match = re.search(r'## 总结与寄语[：:](.*?)$', content, re.DOTALL)

        if summary_match:
            summary_content = summary_match.group(1).strip()
            logger.debug("找到总结与寄语章节")

            # Try to extract core beliefs
            beliefs_match = re.search(
                r'[-*•]\s*核心信念识别[：:](.*?)(?=[-*•]|$)',
                summary_content, re.DOTALL
            )

            # Try to extract growth direction
            growth_match = re.search(
                r'[-*•]\s*成长的核心方向[：:](.*?)(?=[-*•]|$)',
                summary_content, re.DOTALL
            )

            result = {
                "title": "总结与寄语",
                "icon": "🌟",
                "type": "summary",
                "content": summary_content,
                "core_beliefs": beliefs_match.group(1).strip() if beliefs_match else None,
                "growth_direction": growth_match.group(1).strip() if growth_match else None
            }

            logger.info(f"总结章节解析完成，包含核心信念: {result['core_beliefs'] is not None}, 包含成长方向: {result['growth_direction'] is not None}")
            return result

        logger.warning("未找到总结与寄语章节")
        return {
            "title": "总结与寄语",
            "icon": "🌟",
            "type": "summary",
            "content": "你是独特的个体，拥有无限的成长潜力。"
        }

    def _extract_energy_profile(self, content: str) -> Dict[str, Any]:
        """Extract energy profile from Step 2 content"""
        # Try to extract core drive and thinking pattern
        type_match = re.search(r'\*\*核心驱动力\*\*[：:](.*?)(?=\*\*|##|$)', content, re.DOTALL)
        traits_match = re.search(r'\*\*思维模式\*\*[：:](.*?)(?=\*\*|##|$)', content, re.DOTALL)

        type_text = type_match.group(1).strip()[:100] if type_match else "综合型"
        traits_text = traits_match.group(1).strip()[:100] if traits_match else "独特的个人特质"

        return {
            "type": type_text,
            "core_traits": traits_text,
            "description": content[:300] + "..." if len(content) > 300 else content
        }

    def _extract_career_guidance(self, content: str) -> Dict[str, Any]:
        """Extract career guidance from Step 3 content"""
        career_section = re.search(r'## 针对【职业发展】的深度分析(.*?)(?=## 针对|## 总结|$)', content, re.DOTALL)

        if career_section:
            section_text = career_section.group(1)
            return {
                "suitable_paths": ["基于命理配置的职业方向"],
                "work_style": "详见完整报告",
                "development_suggestions": ["详见完整报告中的具体行动方案"]
            }

        return {
            "suitable_paths": ["创意型工作", "分析型工作"],
            "work_style": "根据个人特质灵活调整",
            "development_suggestions": ["持续学习", "发挥优势"]
        }

    def _extract_relationship_pattern(self, content: str) -> Dict[str, Any]:
        """Extract relationship pattern from Step 3 content"""
        relationship_section = re.search(r'## 针对【亲密关系】的深度分析(.*?)(?=## 针对|## 总结|$)', content, re.DOTALL)

        if relationship_section:
            return {
                "style": "详见完整报告",
                "strengths": ["详见完整报告"],
                "challenges": ["详见完整报告"],
                "growth_direction": "详见完整报告中的具体行动方案"
            }

        return {
            "style": "独特的关系互动模式",
            "strengths": ["真诚", "理解"],
            "challenges": ["需要学习的方面"],
            "growth_direction": "持续成长和改善"
        }

    def _extract_personal_growth(self, content: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract personal growth from Step 3 content"""
        selected_topics = user_data.get("selected_topics", [])

        topic_map = {
            "career": "职业发展",
            "relationship": "亲密关系",
            "family": "家庭议题",
            "self": "自我价值",
            "growth": "个人成长",
            "stress": "压力焦虑"
        }

        current_issues = [topic_map.get(t, t) for t in selected_topics]

        return {
            "current_issues": current_issues,
            "action_plan": [
                {
                    "area": "详见完整报告",
                    "action": "详见各议题的具体行动方案",
                    "timeline": "立即开始"
                }
            ],
            "resources": ["详见完整报告中的成长资源推荐"]
        }

    def _extract_summary(self, content: str) -> str:
        """Extract summary from Step 3 content"""
        summary_match = re.search(r'## 总结与寄语(.*?)$', content, re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
        return "你是独特的个体，拥有无限的成长潜力。"


@log_external_api("DeepSeek API")
async def generate_report_with_ai(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call DeepSeek API to generate report
    Supports both multi-step and single-step generation
    """
    # Check if multi-step generation is enabled
    use_multistep = os.getenv("USE_MULTISTEP_GENERATION", "false").lower() == "true"

    if use_multistep:
        logger.info(f"使用多步生成模式 | 用户: {user_data.get('name', 'Unknown')}")
        try:
            generator = MultiStepReportGenerator()
            return await generator.generate_report(user_data)
        except Exception as e:
            logger.error(f"多步生成失败，降级到单步模式: {str(e)}")
            # Fall through to single-step generation

    # Single-step generation (original method)
    return await generate_report_single_step(user_data)


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

        async with httpx.AsyncClient(timeout=60.0) as client:
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
