import re
from typing import Any, Dict, List

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def parse_topic_sections(content: str) -> List[Dict[str, Any]]:
    """Parse topic-specific analysis into structured sections."""
    logger.debug(f"解析议题章节，内容长度: {len(content)}")
    logger.debug(f"议题章节内容预览: {content[:500]}")

    topics = []
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

        pattern_groups = [
            ("模式识别", [
                r'### 1\.\s*模式识别[：:](.*?)(?=###|$)',
                r'### 1\.\s*模式识别\s+(.*?)(?=###|$)',
                r'\*\*模式识别\*\*[：:](.*?)(?=\*\*|###|$)'
            ]),
            ("心理机制", [
                r'### 2\.\s*心理机制[：:](.*?)(?=###|$)',
                r'### 2\.\s*心理机制\s+(.*?)(?=###|$)',
                r'\*\*心理机制\*\*[：:](.*?)(?=\*\*|###|$)'
            ]),
            ("具体行动方案", [
                r'### 3\.\s*具体行动方案[：:](.*?)(?=###|$)',
                r'### 3\.\s*具体行动方案\s+(.*?)(?=###|$)',
                r'\*\*具体行动方案\*\*[：:](.*?)(?=\*\*|###|$)'
            ]),
            ("成长资源", [
                r'### 4\.\s*成长资源[：:](.*?)(?=###|$)',
                r'### 4\.\s*成长资源\s+(.*?)(?=###|$)',
                r'\*\*成长资源\*\*[：:](.*?)(?=\*\*|###|$)'
            ]),
        ]

        for title, patterns in pattern_groups:
            for pattern in patterns:
                section_match = re.search(pattern, topic_content, re.DOTALL)
                if not section_match:
                    continue
                section_content = section_match.group(1).strip()
                subsection = {"title": title, "content": section_content}
                if title == "具体行动方案":
                    subsection["actions"] = _parse_action_items(section_content)
                topic_section["subsections"].append(subsection)
                logger.debug(f"找到 {topic_name} 的{title}")
                break

        if not topic_section["subsections"]:
            logger.warning(f"议题 {topic_name} 未找到任何子章节，使用完整内容")
            topic_section["subsections"].append({
                "title": "分析内容",
                "content": topic_content.strip()
            })

        logger.debug(f"议题 {topic_name} 解析完成，子章节数: {len(topic_section['subsections'])}")
        topics.append(topic_section)

    logger.info(f"议题章节解析完成，议题数: {len(topics)}")
    return topics


def _parse_action_items(content: str) -> List[Dict[str, str]]:
    """Parse action items from content."""
    actions = []
    action_pattern = r'[*\-•]\s*[""""]?(.+?)[""""]?(?:\n|$)'
    for match in re.finditer(action_pattern, content):
        action_text = match.group(1).strip()
        if len(action_text) > 10:
            actions.append({"text": action_text, "completed": False})
    return actions[:5]
