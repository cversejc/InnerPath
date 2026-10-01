"""Pure normalization and validation for report and calendar requests."""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any, Optional

from app.models.service_request import SERVICE_REQUEST_TYPES, ServiceRequest
from app.models.user import User
from app.schemas.calendar import CalendarEntryInput
from app.schemas.service_request import (
    ServiceProfileSnapshot,
    ServiceRequestCreate,
    ServiceRequestUpdate,
)

PUBLIC_STATUS_LABELS = {
    "submitted": "等待咨询师接单",
    "accepted": "咨询师已接单",
    "ai_processing": "正在准备分析",
    "ai_ready": "等待咨询师审校",
    "reviewing": "咨询师审校中",
    "needs_info": "需要补充资料",
    "failed": "分析暂时失败",
    "delivered": "已完成",
    "withdrawn": "已撤回",
    "rejected": "暂未受理",
}
CALENDAR_TONES = {"green", "green-yellow", "yellow-green", "yellow", "red-yellow", "red", "rest"}


def _ensure_service_type(service_type: str) -> None:
    if service_type not in SERVICE_REQUEST_TYPES:
        raise ValueError("invalid_service_type")


def _validate_birth_date(profile: dict[str, Any]) -> None:
    try:
        birth_date = date(
            int(profile["birth_year"]),
            int(profile["birth_month"]),
            int(profile["birth_day"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid_birth_date") from error
    if profile.get("calendar_type") == "lunar" and birth_date.day > 30:
        raise ValueError("invalid_lunar_birth_date")


def _normalize_payload(
    service_type: str,
    profile: dict[str, Any],
    selected_topics: list[str],
    additional_info: Optional[str],
    calendar_goal: Optional[str],
    start_date: Optional[date | str],
) -> dict[str, Any]:
    _ensure_service_type(service_type)
    profile_model = ServiceProfileSnapshot.model_validate(profile)
    profile_payload = profile_model.model_dump(mode="json")
    _validate_birth_date(profile_payload)

    if isinstance(start_date, str) and start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError as error:
            raise ValueError("invalid_calendar_start_date") from error
    else:
        start = start_date

    if service_type == "calendar":
        if start is None:
            raise ValueError("calendar_start_date_required")
        end = start + timedelta(days=29)
    else:
        start = None
        end = None
        calendar_goal = None

    return {
        "profile": profile_payload,
        "selected_topics": list(selected_topics or []),
        "additional_info": additional_info or None,
        "calendar_goal": calendar_goal or None,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
    }


def payload_from_create(data: ServiceRequestCreate, user: User) -> tuple[dict[str, Any], Optional[str]]:
    profile = data.profile.model_dump()
    if not profile.get("name"):
        profile["name"] = user.name
    return (
        _normalize_payload(
            data.service_type,
            profile,
            data.selected_topics,
            data.additional_info,
            data.calendar_goal,
            data.start_date,
        ),
        data.idempotency_key,
    )


def payload_from_update(
    request: ServiceRequest,
    data: ServiceRequestUpdate,
    user: User,
) -> dict[str, Any]:
    current = deepcopy(request.request_payload or {})
    current_profile = deepcopy(current.get("profile") or {})
    if data.profile is not None:
        current_profile.update(data.profile.model_dump(exclude_unset=True))
    if not current_profile.get("name"):
        current_profile["name"] = user.name

    selected_topics = current.get("selected_topics", []) if data.selected_topics is None else data.selected_topics
    additional_info = current.get("additional_info") if data.additional_info is None else data.additional_info
    calendar_goal = current.get("calendar_goal") if data.calendar_goal is None else data.calendar_goal
    start_date = current.get("start_date") if data.start_date is None else data.start_date
    return _normalize_payload(
        request.service_type,
        current_profile,
        selected_topics,
        additional_info,
        calendar_goal,
        start_date,
    )


def flatten_ai_input(request: ServiceRequest) -> dict[str, Any]:
    payload = request.request_payload or {}
    profile = deepcopy(payload.get("profile") or {})
    profile["name"] = profile.get("name") or "用户"
    profile["selected_topics"] = payload.get("selected_topics", [])
    profile["additional_info"] = payload.get("additional_info")
    if request.service_type == "calendar":
        profile["calendar_goal"] = payload.get("calendar_goal")
        profile["start_date"] = payload.get("start_date")
        profile["end_date"] = payload.get("end_date")
    return profile


def normalize_report_draft(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": report_data.get("title") or "辰鉴·人生说明书",
        "basic_info": report_data.get("basic_info") or {},
        "foundation_data": report_data.get("foundation_data"),
        "structured_sections": report_data.get("structured_sections") or report_data.get("structuredSections"),
        "energy_profile": report_data.get("energy_profile") or {},
        "career_guidance": report_data.get("career_guidance") or {},
        "relationship_pattern": report_data.get("relationship_pattern") or {},
        "personal_growth": report_data.get("personal_growth") or {},
        "summary": report_data.get("summary") or "",
        "ai_generated_content": report_data.get("ai_generated_content"),
    }


def normalize_calendar_draft(calendar_data: dict[str, Any], request: ServiceRequest) -> dict[str, Any]:
    payload = request.request_payload or {}
    entries = calendar_data.get("entries") or []
    return {
        "title": calendar_data.get("title") or "辰鉴·你的决策时机说明书",
        # The application snapshot is authoritative.  AI may describe entries,
        # but it cannot silently expand or shift the user's requested window.
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "meta_payload": calendar_data.get("meta_payload") or {
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
    _ensure_service_type(service_type)
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
            any(key not in draft or not isinstance(draft.get(key), dict) or not draft.get(key) for key in required[:-1])
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
        if not (entry.keyword or "").strip() or not (entry.status_label or "").strip() or not (entry.summary or "").strip():
            raise ValueError("calendar_entry_incomplete")
        normalized_entries.append(entry.model_dump(mode="json"))

    if set(expected_dates) != seen_dates:
        raise ValueError("calendar_entries_incomplete")
    draft["entries"] = sorted(normalized_entries, key=lambda entry: entry["entry_date"])
    draft["title"] = draft.get("title") or "辰鉴·你的决策时机说明书"
    draft["meta_payload"] = draft.get("meta_payload") or {}
    return draft
