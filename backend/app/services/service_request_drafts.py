"""Normalization and validation for AI-generated report and calendar drafts."""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

from app.models.service_request import ServiceRequest
from app.schemas.calendar import CalendarEntryInput
from app.services.service_request_payloads import ensure_service_type

CALENDAR_TONES = {
    "green",
    "green-yellow",
    "yellow-green",
    "yellow",
    "red-yellow",
    "red",
    "rest",
}


def normalize_report_draft(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": report_data.get("title") or "辰鉴·人生说明书",
        "basic_info": report_data.get("basic_info") or {},
        "foundation_data": report_data.get("foundation_data"),
        "structured_sections": report_data.get("structured_sections")
        or report_data.get("structuredSections"),
        "energy_profile": report_data.get("energy_profile") or {},
        "career_guidance": report_data.get("career_guidance") or {},
        "relationship_pattern": report_data.get("relationship_pattern") or {},
        "personal_growth": report_data.get("personal_growth") or {},
        "summary": report_data.get("summary") or "",
        "ai_generated_content": report_data.get("ai_generated_content"),
    }


def normalize_calendar_draft(
    calendar_data: dict[str, Any], request: ServiceRequest
) -> dict[str, Any]:
    payload = request.request_payload or {}
    entries = calendar_data.get("entries") or []
    return {
        "title": calendar_data.get("title") or "辰鉴·你的决策时机说明书",
        # The application snapshot is authoritative. AI may describe entries,
        # but it cannot silently expand or shift the user's requested window.
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "meta_payload": calendar_data.get("meta_payload")
        or {
            "subtitle": "PERSONAL TIMEZONE",
            "rhythm": "少说，多做，多记录",
            "intro": "这是一张属于你的决策时机参照系，帮你在重要选择前留出观察、行动与复盘的空间。",
            "overview": [],
            "pillars": "",
        },
        "entries": entries,
    }


def _calendar_dates(start_date: str, end_date: str) -> list[date]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    return [start + timedelta(days=index) for index in range((end - start).days + 1)]


def validate_draft(service_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_service_type(service_type)
    draft = deepcopy(payload or {})
    if service_type == "report":
        required = (
            "energy_profile",
            "career_guidance",
            "relationship_pattern",
            "personal_growth",
            "summary",
        )
        if (
            any(
                key not in draft
                or not isinstance(draft.get(key), dict)
                or not draft.get(key)
                for key in required[:-1]
            )
            or not isinstance(draft.get("summary"), str)
            or not draft.get("summary", "").strip()
        ):
            raise ValueError("report_draft_incomplete")
        draft["title"] = draft.get("title") or "辰鉴·人生说明书"
        return draft

    start_date = draft.get("start_date")
    end_date = draft.get("end_date")
    if not start_date or not end_date:
        raise ValueError("calendar_draft_range_required")
    try:
        expected_dates = _calendar_dates(start_date, end_date)
    except ValueError as error:
        raise ValueError("invalid_calendar_draft_range") from error
    if len(expected_dates) != 30:
        raise ValueError("calendar_draft_must_cover_30_days")

    normalized_entries = []
    seen_dates: set[date] = set()
    for raw_entry in draft.get("entries") or []:
        try:
            entry = CalendarEntryInput.model_validate(raw_entry)
        except ValueError as error:
            raise ValueError("invalid_calendar_entry") from error
        if entry.entry_date in seen_dates:
            raise ValueError("duplicate_calendar_entry_date")
        seen_dates.add(entry.entry_date)
        if entry.entry_date not in expected_dates:
            raise ValueError("calendar_entry_outside_range")
        if entry.tone and entry.tone not in CALENDAR_TONES:
            raise ValueError("invalid_calendar_entry")
        if (
            not (entry.keyword or "").strip()
            or not (entry.status_label or "").strip()
            or not (entry.summary or "").strip()
        ):
            raise ValueError("calendar_entry_incomplete")
        normalized_entries.append(entry.model_dump(mode="json"))

    if set(expected_dates) != seen_dates:
        raise ValueError("calendar_entries_incomplete")
    draft["entries"] = sorted(normalized_entries, key=lambda entry: entry["entry_date"])
    draft["title"] = draft.get("title") or "辰鉴·你的决策时机说明书"
    draft["meta_payload"] = draft.get("meta_payload") or {}
    return draft
