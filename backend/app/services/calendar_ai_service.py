"""AI generation for a private, consultant-reviewed decision calendar draft."""

import json
from typing import Any, Dict

import httpx

from app.config import settings
from app.core.logging_config import get_logger


logger = get_logger(__name__)


def _extract_content(response_data: dict[str, Any]) -> str:
    choices = response_data.get("choices") or []
    if not choices:
        raise ValueError("calendar_ai_empty_response")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    if not isinstance(content, str) or not content.strip():
        raise ValueError("calendar_ai_empty_content")
    return content.strip()


def _parse_json_content(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ValueError("calendar_ai_invalid_json") from error
    if not isinstance(parsed, dict):
        raise ValueError("calendar_ai_invalid_payload")
    return parsed


def build_calendar_prompt(user_data: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "profile": {
                "name": user_data.get("name"),
                "gender": user_data.get("gender"),
                "birth_year": user_data.get("birth_year"),
                "birth_month": user_data.get("birth_month"),
                "birth_day": user_data.get("birth_day"),
                "birth_hour": user_data.get("birth_hour"),
                "birth_minute": user_data.get("birth_minute"),
                "birth_place": user_data.get("birth_place"),
                "calendar_type": user_data.get("calendar_type", "solar"),
            },
            "service_request": {
                "start_date": user_data.get("start_date"),
                "end_date": user_data.get("end_date"),
                "selected_topics": user_data.get("selected_topics", []),
                "goal": user_data.get("calendar_goal"),
                "additional_info": user_data.get("additional_info"),
            },
        },
        ensure_ascii=False,
        indent=2,
    )


async def generate_calendar_with_ai(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate strict JSON that is validated again before it becomes a draft."""

    prompt = build_calendar_prompt(user_data)
    system_prompt = """你是辰鉴的决策日历初稿助手。

你的工作是根据用户资料与指定的 30 天范围，生成一份供咨询师审校的日历初稿。
这不是命运预测，也不是医疗、法律或财务建议。请使用温和、具体、保留主体性的表达，
把每天的内容写成观察、行动、等待和复盘的参照，不使用绝对因果或恐吓表达。

只返回合法 JSON，不要 Markdown 代码块，不要额外解释。JSON 结构必须为：
{
  "title": "字符串",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "meta_payload": {
    "subtitle": "字符串",
    "rhythm": "字符串",
    "intro": "字符串",
    "overview": ["字符串"],
    "pillars": "字符串"
  },
  "entries": [
    {
      "entry_date": "YYYY-MM-DD",
      "day_pillar": "字符串或空字符串",
      "tone": "green/yellow/rest/red",
      "status_label": "简短状态",
      "keyword": "简短关键词",
      "summary": "当天的一段简短说明",
      "suitable": ["适合事项"],
      "unsuitable": ["不适合事项"],
      "time_window": "时间节奏建议",
      "admin_note": "给咨询师的内部备注，可为空"
    }
  ]
}

必须覆盖输入的全部 30 天，日期不能重复，也不能超出范围。"""

    logger.info("开始生成决策日历 AI 初稿 | start=%s", user_data.get("start_date"))
    async with httpx.AsyncClient(timeout=settings.DEEPSEEK_TIMEOUT_SECONDS) as client:
        response = await client.post(
            settings.DEEPSEEK_API_URL,
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.6,
                "max_tokens": settings.DEEPSEEK_MAX_TOKENS,
                "stream": False,
                "thinking": {"type": "enabled" if settings.DEEPSEEK_THINKING else "disabled"},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            },
        )
        response.raise_for_status()
        parsed = _parse_json_content(_extract_content(response.json()))
        parsed["start_date"] = parsed.get("start_date") or user_data.get("start_date")
        parsed["end_date"] = parsed.get("end_date") or user_data.get("end_date")
        return parsed

