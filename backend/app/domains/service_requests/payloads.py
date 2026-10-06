"""Normalize submitted report and calendar request payloads."""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any, Optional

from .models import SERVICE_REQUEST_TYPES, ServiceRequest
from app.models.user import User
from app.domains.users.lunar_calendar import solar_date_for_birth
from .schemas import (
    ReportContext,
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
        solar_date_for_birth(
            int(profile["birth_year"]),
            int(profile["birth_month"]),
            int(profile["birth_day"]),
            calendar_type=profile.get("calendar_type", "solar"),
            is_leap_month=bool(profile.get("birth_is_leap_month", False)),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid_birth_date") from error


def _normalize_payload(
    service_type: str,
    profile: dict[str, Any],
    selected_topics: list[str],
    additional_info: Optional[str],
    calendar_goal: Optional[str],
    start_date: Optional[date | str],
    *,
    context: Optional[dict[str, Any]] = None,
    profile_version: Optional[int] = None,
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

    normalized_context = None
    if service_type == "report":
        normalized_context = ReportContext.model_validate(context or {}).model_dump(mode="json")
        for field in ("current_challenge", "decision_description", "additional_info"):
            value = normalized_context.get(field)
            normalized_context[field] = value.strip() or None if isinstance(value, str) else value
        if not normalized_context["focus_topics"]:
            raise ValueError("report_request_requires_focus_topics")
        if not normalized_context["current_challenge"]:
            raise ValueError("report_request_requires_current_challenge")
        if not normalized_context["expected_outcomes"]:
            raise ValueError("report_request_requires_expected_outcomes")
        if profile_version is not None and int(profile_version) < 1:
            raise ValueError("invalid_profile_version")

    normalized = {
        "profile": profile_payload,
        "selected_topics": list(selected_topics or []),
        "additional_info": additional_info or None,
        "calendar_goal": calendar_goal or None,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
    }
    if normalized_context is not None:
        normalized["context"] = normalized_context
        normalized["selected_topics"] = normalized_context["focus_topics"]
        normalized["additional_info"] = normalized_context["additional_info"]
    if service_type == "report" and profile_version is not None:
        normalized["profile_version"] = int(profile_version)
    return normalized


def payload_from_create(
    data: ServiceRequestCreate, user: User
) -> tuple[dict[str, Any], Optional[str]]:
    if (
        data.service_type == "report"
        and data.profile_version is not None
        and int(data.profile_version) != int(user.profile_version or 1)
    ):
        raise ValueError("profile_version_conflict")
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
            context=data.context.model_dump() if data.context is not None else None,
            profile_version=data.profile_version or user.profile_version or 1,
        ),
        data.idempotency_key,
    )


def payload_from_update(
    request: ServiceRequest,
    data: ServiceRequestUpdate,
    user: User,
) -> dict[str, Any]:
    if (
        request.service_type == "report"
        and data.profile_version is not None
        and int(data.profile_version) != int(user.profile_version or 1)
    ):
        raise ValueError("profile_version_conflict")
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
    context = (
        current.get("context")
        if data.context is None
        else data.context.model_dump()
    )
    profile_version = (
        current.get("profile_version")
        if data.profile_version is None
        else data.profile_version
    )
    return _normalize_payload(
        request.service_type,
        current_profile,
        selected_topics,
        additional_info,
        calendar_goal,
        start_date,
        context=context,
        profile_version=profile_version or user.profile_version or 1,
    )


def flatten_ai_input(request: ServiceRequest) -> dict[str, Any]:
    payload = request.request_payload or {}
    profile = deepcopy(payload.get("profile") or {})
    profile["name"] = profile.get("name") or "用户"
    profile["selected_topics"] = payload.get("selected_topics", [])
    profile["additional_info"] = payload.get("additional_info")
    profile["context"] = deepcopy(payload.get("context") or {})
    if request.service_type == "calendar":
        profile["calendar_goal"] = payload.get("calendar_goal")
        profile["start_date"] = payload.get("start_date")
        profile["end_date"] = payload.get("end_date")
    return profile
