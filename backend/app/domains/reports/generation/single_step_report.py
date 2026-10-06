from typing import Any, Dict

import httpx

from app.core.logging_config import get_logger
from app.services.llm import chat
from .fallback_report import generate_basic_report
from .mingli_foundation import calculate_mingli_foundation
from .report_prompt import SYSTEM_PROMPT, build_prompt
from .report_response_parser import parse_ai_response

logger = get_logger(__name__)


async def generate_report_single_step(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a report with one AI request, falling back to a basic report on errors."""
    logger.info(
        f"开始生成 AI 报告（单步模式）| 用户: {user_data.get('name', 'Unknown')}"
    )

    prompt_user_data = dict(user_data)
    foundation_data = calculate_mingli_foundation(user_data)
    prompt_user_data["foundation_data"] = foundation_data
    logger.info("单步模式已注入确定性命理基础")

    prompt = build_prompt(prompt_user_data)
    logger.debug(f"Prompt 长度: {len(prompt)} 字符")

    try:
        logger.info("调用统一大模型对话接口")
        completion = await chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        ai_content = completion.content
        logger.info(
            "大模型调用成功 | provider=%s | model=%s | thinking=%s | finish=%s | chars=%s",
            completion.provider,
            completion.model,
            completion.thinking_enabled,
            completion.finish_reason,
            len(ai_content),
        )
        logger.debug(f"AI 响应预览: {ai_content[:200]}...")

        result = parse_ai_response(ai_content, user_data)
        result["basic_info"]["generated_by"] = "AI"
        if prompt_user_data.get("foundation_data"):
            result["foundation_data"] = prompt_user_data["foundation_data"]
            result["basic_info"]["generated_by"] = "AI + Deterministic Mingli"
        logger.info(f"AI 报告解析完成 | 包含字段: {list(result.keys())}")

        return result

    except httpx.HTTPStatusError as error:
        logger.error(
            f"大模型 HTTP 错误 | 状态码: {error.response.status_code}"
        )
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
    except httpx.TimeoutException:
        logger.error("大模型调用超时")
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
    except Exception as error:
        logger.error(f"大模型调用失败: {str(error)}", exc_info=True)
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
