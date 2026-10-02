import re
from typing import Any, Dict


class MultiStepReportSections:
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
