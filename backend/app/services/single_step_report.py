from typing import Any, Dict

import httpx

from app.config import settings
from app.core.logging_config import get_logger
from app.services.fallback_report import generate_basic_report
from app.services.mingli_foundation import calculate_mingli_foundation
from app.services.report_prompt import SYSTEM_PROMPT, build_prompt
from app.services.report_response_parser import extract_chat_content, parse_ai_response

logger = get_logger("app.services.ai_service")


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
        logger.info(f"调用 DeepSeek API | URL: {settings.DEEPSEEK_API_URL}")

        async with httpx.AsyncClient(
            timeout=settings.DEEPSEEK_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(
                settings.DEEPSEEK_API_URL,
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": settings.DEEPSEEK_MAX_TOKENS,
                    "stream": False,
                    "thinking": {
                        "type": "enabled" if settings.DEEPSEEK_THINKING else "disabled"
                    },
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                },
            )

            response.raise_for_status()
            response_data = response.json()
            ai_content = extract_chat_content(response_data)

            finish_reason = (response_data.get("choices") or [{}])[0].get(
                "finish_reason"
            )
            logger.info(
                f"DeepSeek API 调用成功 | 模型: {settings.DEEPSEEK_MODEL} | "
                f"思考模式: {'enabled' if settings.DEEPSEEK_THINKING else 'disabled'} | "
                f"结束原因: {finish_reason} | 响应长度: {len(ai_content)} 字符"
            )
            logger.debug(f"AI 响应预览: {ai_content[:200]}...")

            result = parse_ai_response(ai_content, user_data)
            if prompt_user_data.get("foundation_data"):
                result["foundation_data"] = prompt_user_data["foundation_data"]
                result["basic_info"][
                    "generated_by"
                ] = "DeepSeek AI + Deterministic Mingli"
            logger.info(f"AI 报告解析完成 | 包含字段: {list(result.keys())}")

            return result

    except httpx.HTTPStatusError as error:
        logger.error(
            f"DeepSeek API HTTP 错误 | 状态码: {error.response.status_code} | "
            f"响应: {error.response.text}"
        )
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
    except httpx.TimeoutException:
        logger.error("DeepSeek API 调用超时")
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
    except Exception as error:
        logger.error(f"DeepSeek API 调用失败: {str(error)}", exc_info=True)
        logger.warning("使用降级方案生成报告")
        return generate_basic_report(user_data)
