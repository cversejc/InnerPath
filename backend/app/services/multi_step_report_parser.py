import re
from typing import Any, Dict, List

from app.core.logging_config import get_logger

logger = get_logger("app.services.ai_service")


class MultiStepReportParser:
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

