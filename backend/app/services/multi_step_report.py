import httpx
import json
from typing import Any, Dict

from app.config import settings
from app.core.logging_config import get_logger
from app.services.bazi_calculator import calculate_mingli_foundation
from app.services.multi_step_report_parser import MultiStepReportParser
from app.services.multi_step_report_prompts import MultiStepReportPrompts
from app.services.multi_step_report_sections import MultiStepReportSections
from app.services.single_step_report import _extract_chat_content

logger = get_logger("app.services.ai_service")

class MultiStepReportGenerator(
    MultiStepReportPrompts,
    MultiStepReportParser,
    MultiStepReportSections,
):
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

    async def _call_ai(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000
    ) -> str:
        """Call DeepSeek API with given prompt"""
        async with httpx.AsyncClient(timeout=settings.DEEPSEEK_TIMEOUT_SECONDS) as client:
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
                    "max_tokens": max_tokens,
                    "stream": False,
                    "thinking": {
                        "type": "enabled" if settings.DEEPSEEK_THINKING else "disabled"
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )

            response.raise_for_status()
            response_data = response.json()
            return _extract_chat_content(response_data)

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
