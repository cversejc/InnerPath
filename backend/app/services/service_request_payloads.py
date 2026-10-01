"""Normalize submitted report and calendar request payloads."""

from copy import deepcopy
from datetime import date
from typing import Any, Optional

from app.models.service_request import SERVICE_REQUEST_TYPES, ServiceRequest
from app.models.user import User
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


def ensure_service_type(service_type: str) -> None:
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
    ensure_service_type(service_type)
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


def payload_from_create(
    data: ServiceRequestCreate, user: User
) -> tuple[dict[str, Any], Optional[str]]:
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

    selected_topics = (
        current.get("selected_topics", [])
        if data.selected_topics is None
        else data.selected_topics
    )
    additional_info = (
        current.get("additional_info")
        if data.additional_info is None
        else data.additional_info
    )
    calendar_goal = (
        current.get("calendar_goal")
        if data.calendar_goal is None
        else data.calendar_goal
    )
    start_date = (
        current.get("start_date") if data.start_date is None else data.start_date
    )
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
