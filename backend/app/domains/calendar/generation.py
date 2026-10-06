"""AI generation for a user-ready calendar based on a delivered report."""

import json
from datetime import date, timedelta
from typing import Any, Dict

from pydantic import ValidationError

from app.core.logging_config import get_logger
from app.domains.calendar.schemas import CalendarCreate, CalendarEntryInput
from app.services.llm import chat


logger = get_logger(__name__)


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
                "usage_scenario": user_data.get("usage_scenario"),
                "goal": user_data.get("calendar_goal"),
                "decision_description": user_data.get("decision_description"),
                "expected_outcomes": user_data.get("expected_outcomes", []),
                "additional_info": user_data.get("additional_info"),
            },
            "source_report": user_data.get("source_report") or {},
        },
        ensure_ascii=False,
        indent=2,
    )


async def generate_calendar_with_ai(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate strict JSON for a calendar that is validated before delivery."""

    prompt = build_calendar_prompt(user_data)
    system_prompt = """你是辰鉴的个人决策日历生成助手。用户已经收到来源报告，并主动点击生成。

你的工作是以来源报告中的已交付内容为依据，结合用户本次填写的目标与指定 30 天范围，
生成可以直接交付给用户使用的决策日历。不要增加报告没有支持的人格判断或结论。
这不是命运预测，也不是医疗、法律或财务建议。请使用温和、具体、保留主体性的表达，
把每天的内容写成观察、行动、等待和复盘的参照，不使用绝对因果、恐吓或保证结果的表达。
不得声称报告以外的诊断或事实；每条建议都要保持可选择、可调整。

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
      "admin_note": "留空字符串"
    }
  ]
}

必须覆盖输入的全部 30 天，日期不能重复，也不能超出范围。结合已交付报告的具体特质与本次目标，避免照搬通用建议。不得声称报告以外的诊断或事实；每条建议都要保持可选择、可调整。"""

    logger.info("开始生成决策日历 AI 初稿 | start=%s", user_data.get("start_date"))
    completion = await chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
    )
    parsed = _parse_json_content(completion.content)
    parsed["start_date"] = parsed.get("start_date") or user_data.get("start_date")
    parsed["end_date"] = parsed.get("end_date") or user_data.get("end_date")
    return parsed


def validate_generated_calendar(
    payload: dict[str, Any], user_data: Dict[str, Any]
) -> CalendarCreate:
    try:
        start_date = date.fromisoformat(str(user_data["start_date"]))
        end_date = date.fromisoformat(str(user_data["end_date"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("calendar_request_requires_date_range") from error

    if (end_date - start_date).days != 29:
        raise ValueError("calendar_request_requires_30_days")
    if not isinstance(payload, dict):
        raise ValueError("calendar_ai_invalid_payload")

    try:
        output_start = date.fromisoformat(str(payload.get("start_date") or start_date))
        output_end = date.fromisoformat(str(payload.get("end_date") or end_date))
        if output_start != start_date or output_end != end_date:
            raise ValueError("calendar_ai_range_mismatch")

        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list) or len(raw_entries) != 30:
            raise ValueError("calendar_ai_incomplete_dates")
        entries = [CalendarEntryInput.model_validate(item) for item in raw_entries]
        actual_dates = [entry.entry_date for entry in entries]
        expected_dates = [start_date + timedelta(days=index) for index in range(30)]
        if len(set(actual_dates)) != 30 or sorted(actual_dates) != expected_dates:
            raise ValueError("calendar_ai_incomplete_dates")
        if any(
            not (entry.status_label or "").strip()
            or not (entry.keyword or "").strip()
            or not (entry.summary or "").strip()
            for entry in entries
        ):
            raise ValueError("calendar_ai_entry_content_missing")
        if any(
            entry.tone
            and entry.tone not in {
                "green",
                "blue",
                "yellow",
                "rest",
                "red",
                "green-yellow",
                "yellow-green",
                "red-yellow",
            }
            for entry in entries
        ):
            raise ValueError("calendar_ai_invalid_tone")

        return CalendarCreate(
            title=payload.get("title") or "辰鉴·决策日历",
            start_date=start_date,
            end_date=end_date,
            meta_payload=payload.get("meta_payload") or {},
            entries=entries,
        )
    except ValidationError as error:
        raise ValueError("calendar_ai_invalid_payload") from error

