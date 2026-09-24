"""Business workflow for consultant-assisted report and calendar delivery."""

from copy import deepcopy
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any, Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models.calendar import CalendarEntry, UserCalendar
from app.models.report import Report
from app.models.service_request import (
    SERVICE_REQUEST_STATUSES,
    SERVICE_REQUEST_TYPES,
    ServiceRequest,
    ServiceRequestDraft,
    ServiceRequestRevision,
    ServiceRequestTask,
)
from app.models.user import User
from app.schemas.calendar import CalendarEntryInput
from app.schemas.service_request import (
    ServiceProfileSnapshot,
    ServiceRequestCreate,
    ServiceRequestDraftUpdate,
    ServiceRequestInfoInput,
    ServiceRequestUpdate,
)
from app.services.audit_service import record_audit


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


async def _get_request_for_update(db: AsyncSession, request_id: int) -> Optional[ServiceRequest]:
    result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def _get_draft(db: AsyncSession, request_id: int) -> Optional[ServiceRequestDraft]:
    result = await db.execute(
        select(ServiceRequestDraft).where(ServiceRequestDraft.request_id == request_id)
    )
    return result.scalar_one_or_none()


async def _get_draft_for_update(db: AsyncSession, request_id: int) -> Optional[ServiceRequestDraft]:
    result = await db.execute(
        select(ServiceRequestDraft)
        .where(ServiceRequestDraft.request_id == request_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _get_latest_task(db: AsyncSession, request_id: int) -> Optional[ServiceRequestTask]:
    result = await db.execute(
        select(ServiceRequestTask)
        .where(ServiceRequestTask.request_id == request_id)
        .order_by(ServiceRequestTask.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _append_revision(
    db: AsyncSession,
    request_id: int,
    stage: str,
    payload: dict[str, Any],
    created_by: Optional[int],
) -> ServiceRequestRevision:
    version = int(
        await db.scalar(
            select(func.max(ServiceRequestRevision.version_number)).where(
                ServiceRequestRevision.request_id == request_id
            )
        )
        or 0
    ) + 1
    revision = ServiceRequestRevision(
        request_id=request_id,
        version_number=version,
        stage=stage,
        payload=deepcopy(payload),
        created_by=created_by,
    )
    db.add(revision)
    await db.flush()
    return revision


async def create_service_request(
    db: AsyncSession,
    user: User,
    data: ServiceRequestCreate,
    request: Optional[Request] = None,
) -> ServiceRequest:
    payload, idempotency_key = payload_from_create(data, user)
    if idempotency_key:
        existing = await db.scalar(
            select(ServiceRequest).where(
                ServiceRequest.user_id == user.id,
                ServiceRequest.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing

    service_request = ServiceRequest(
        user_id=user.id,
        service_type=data.service_type,
        status="submitted",
        request_payload=payload,
        idempotency_key=idempotency_key,
    )
    db.add(service_request)
    try:
        await db.flush()
        await record_audit(
            db,
            user.id,
            "service_request.create",
            "service_request",
            str(service_request.id),
            target_user_id=user.id,
            details={"service_type": data.service_type},
            request=request,
        )
        await db.commit()
    except IntegrityError:
        # A double submit can race the lookup above.  The unique constraint is
        # the final idempotency guard; return the request created by the other
        # transaction when it wins the race.
        await db.rollback()
        if idempotency_key:
            existing = await db.scalar(
                select(ServiceRequest).where(
                    ServiceRequest.user_id == user.id,
                    ServiceRequest.idempotency_key == idempotency_key,
                )
            )
            if existing:
                return existing
        raise
    await db.refresh(service_request)
    return service_request


async def get_user_service_requests(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
) -> list[ServiceRequest]:
    query = select(ServiceRequest).where(ServiceRequest.user_id == user_id)
    if status:
        query = query.where(ServiceRequest.status == status)
    if service_type:
        query = query.where(ServiceRequest.service_type == service_type)
    result = await db.execute(query.order_by(ServiceRequest.created_at.desc()))
    return list(result.scalars().all())


async def get_service_request(db: AsyncSession, request_id: int) -> Optional[ServiceRequest]:
    return await db.get(ServiceRequest, request_id)


async def update_user_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    user: User,
    data: ServiceRequestUpdate,
    request: Optional[Request] = None,
) -> ServiceRequest:
    if service_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None or locked_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if service_request.status not in {"submitted", "needs_info"}:
        raise ValueError("service_request_locked")
    service_request.request_payload = payload_from_update(service_request, data, user)
    service_request.updated_by = user.id
    await record_audit(
        db,
        user.id,
        "service_request.update",
        "service_request",
        str(service_request.id),
        target_user_id=user.id,
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request


async def resubmit_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    user: User,
    request: Optional[Request] = None,
) -> ServiceRequest:
    if service_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None or locked_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if service_request.status != "needs_info":
        raise ValueError("service_request_not_waiting_for_info")
    _normalize_payload(
        service_request.service_type,
        (service_request.request_payload or {}).get("profile") or {},
        (service_request.request_payload or {}).get("selected_topics", []),
        (service_request.request_payload or {}).get("additional_info"),
        (service_request.request_payload or {}).get("calendar_goal"),
        (service_request.request_payload or {}).get("start_date"),
    )
    old_draft = await _get_draft(db, service_request.id)
    if old_draft:
        await _append_revision(db, service_request.id, "before_resubmit", old_draft.editable_payload, user.id)
        await db.delete(old_draft)
    service_request.status = "accepted" if service_request.assigned_consultant_id else "submitted"
    if service_request.assigned_consultant_id:
        service_request.accepted_at = datetime.utcnow()
    service_request.needs_info_reason = None
    service_request.last_error = None
    service_request.updated_by = user.id
    await record_audit(
        db,
        user.id,
        "service_request.resubmit",
        "service_request",
        str(service_request.id),
        target_user_id=user.id,
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request


async def withdraw_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    user: User,
    request: Optional[Request] = None,
) -> ServiceRequest:
    if service_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None or locked_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if service_request.status not in {"submitted", "needs_info"}:
        raise ValueError("service_request_cannot_withdraw")
    service_request.status = "withdrawn"
    service_request.withdrawn_at = datetime.utcnow()
    service_request.updated_by = user.id
    await record_audit(
        db,
        user.id,
        "service_request.withdraw",
        "service_request",
        str(service_request.id),
        target_user_id=user.id,
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request


async def accept_service_request(
    db: AsyncSession,
    request_id: int,
    consultant: User,
    request: Optional[Request] = None,
) -> ServiceRequest:
    service_request = await _get_request_for_update(db, request_id)
    if service_request is None:
        raise ValueError("service_request_not_found")
    if service_request.status == "accepted" and service_request.assigned_consultant_id == consultant.id:
        return service_request
    if service_request.status != "submitted" or service_request.assigned_consultant_id is not None:
        raise ValueError("service_request_already_taken")
    service_request.assigned_consultant_id = consultant.id
    service_request.status = "accepted"
    service_request.accepted_at = datetime.utcnow()
    service_request.updated_by = consultant.id
    await record_audit(
        db,
        consultant.id,
        "service_request.accept",
        "service_request",
        str(request_id),
        target_user_id=service_request.user_id,
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request


def staff_can_access(service_request: ServiceRequest, user: User) -> bool:
    return user.role == "admin" or service_request.assigned_consultant_id == user.id


async def list_staff_service_requests(
    db: AsyncSession,
    user: User,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    scope: str = "mine",
) -> list[tuple[ServiceRequest, Optional[User]]]:
    query = select(ServiceRequest, User).join(User, User.id == ServiceRequest.user_id)
    if user.role != "admin":
        if scope == "available":
            query = query.where(
                ServiceRequest.status == "submitted",
                ServiceRequest.assigned_consultant_id.is_(None),
            )
        else:
            query = query.where(ServiceRequest.assigned_consultant_id == user.id)
    elif scope == "available":
        query = query.where(
            ServiceRequest.status == "submitted",
            ServiceRequest.assigned_consultant_id.is_(None),
        )
    elif scope == "mine":
        query = query.where(ServiceRequest.assigned_consultant_id == user.id)
    if status:
        query = query.where(ServiceRequest.status == status)
    if service_type:
        query = query.where(ServiceRequest.service_type == service_type)
    result = await db.execute(query.order_by(ServiceRequest.created_at.desc()))
    return list(result.all())


async def get_workspace(
    db: AsyncSession,
    service_request: ServiceRequest,
) -> dict[str, Any]:
    user = await db.get(User, service_request.user_id)
    consultant_name = None
    if service_request.assigned_consultant_id:
        consultant_name = await db.scalar(
            select(User.name).where(User.id == service_request.assigned_consultant_id)
        )
    draft = await _get_draft(db, service_request.id)
    task = await _get_latest_task(db, service_request.id)
    return {
        "request": serialize_service_request(service_request, consultant_name=consultant_name),
        "user": serialize_staff_user(user),
        "draft": draft,
        "task": task,
    }


def serialize_staff_user(user: Optional[User]) -> dict[str, Any]:
    if user is None:
        return {}
    return {
        "id": user.id,
        "name": user.name,
        "phone": user.phone,
        "gender": user.gender,
        "birth_year": user.birth_year,
        "birth_month": user.birth_month,
        "birth_day": user.birth_day,
        "birth_hour": user.birth_hour,
        "birth_minute": user.birth_minute,
        "birth_place": user.birth_place,
        "role": user.role,
    }


def serialize_service_request(
    service_request: ServiceRequest,
    consultant_name: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "id": service_request.id,
        "service_type": service_request.service_type,
        "status": service_request.status,
        "request_payload": deepcopy(service_request.request_payload or {}),
        "result_type": service_request.result_type,
        "result_id": service_request.result_id,
        "assigned_consultant_id": service_request.assigned_consultant_id,
        "needs_info_reason": service_request.needs_info_reason,
        "rejection_reason": service_request.rejection_reason,
        "last_error": service_request.last_error,
        "assigned_consultant_name": consultant_name,
        "created_at": service_request.created_at,
        "updated_at": service_request.updated_at,
        "accepted_at": service_request.accepted_at,
        "ai_started_at": service_request.ai_started_at,
        "ai_completed_at": service_request.ai_completed_at,
        "reviewing_at": service_request.reviewing_at,
        "needs_info_at": service_request.needs_info_at,
        "failed_at": service_request.failed_at,
        "delivered_at": service_request.delivered_at,
        "withdrawn_at": service_request.withdrawn_at,
        "rejected_at": service_request.rejected_at,
    }


def serialize_task(task: Optional[ServiceRequestTask]) -> Optional[dict[str, Any]]:
    if task is None:
        return None
    return {
        "task_id": task.task_id,
        "request_id": task.request_id,
        "service_type": task.service_type,
        "status": task.status,
        "progress": task.progress,
        "error": task.error,
        "retry_count": task.retry_count,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


async def enqueue_ai_draft(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    request: Optional[Request] = None,
    *,
    force: bool = False,
    retry_of_task_id: Optional[str] = None,
) -> ServiceRequestTask:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    allowed_statuses = {"accepted", "failed"}
    if force:
        allowed_statuses.update({"ai_ready", "reviewing"})
    if service_request.status not in allowed_statuses:
        raise ValueError("ai_draft_not_allowed")
    active = await db.scalar(
        select(ServiceRequestTask).where(
            ServiceRequestTask.request_id == service_request.id,
            ServiceRequestTask.status == "processing",
        )
    )
    if active:
        return active

    draft = await _get_draft(db, service_request.id)
    if force and draft:
        await _append_revision(db, service_request.id, "before_ai_regeneration", draft.editable_payload, actor.id)

    parent_task = None
    if retry_of_task_id is None:
        latest_task = await _get_latest_task(db, service_request.id)
        if latest_task and latest_task.status in {"failed", "completed"}:
            retry_of_task_id = latest_task.task_id
    if retry_of_task_id:
        parent_task = await db.get(ServiceRequestTask, retry_of_task_id)

    task_id = str(uuid4())
    task = ServiceRequestTask(
        task_id=task_id,
        request_id=service_request.id,
        service_type=service_request.service_type,
        status="processing",
        progress=0,
        input_snapshot=deepcopy(service_request.request_payload),
        retry_count=(parent_task.retry_count + 1) if parent_task else 0,
        retry_of_task_id=retry_of_task_id,
    )
    db.add(task)
    service_request.status = "ai_processing"
    service_request.ai_started_at = datetime.utcnow()
    service_request.failed_at = None
    service_request.last_error = None
    service_request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "service_request.ai.start",
        "service_request",
        str(service_request.id),
        target_user_id=service_request.user_id,
        details={"service_type": service_request.service_type, "task_id": task_id},
        request=request,
    )
    await db.commit()
    await db.refresh(task)

    from app.tasks.service_request_tasks import generate_service_request_task

    generate_service_request_task.apply_async(args=[service_request.id], task_id=task_id)
    return task


async def save_service_request_draft(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    data: ServiceRequestDraftUpdate,
    request: Optional[Request] = None,
) -> ServiceRequestDraft:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    if service_request.status not in {"ai_ready", "reviewing"}:
        raise ValueError("draft_save_not_allowed")
    draft = await _get_draft_for_update(db, service_request.id)
    if draft is None:
        raise ValueError("service_request_draft_not_found")
    if data.expected_version is not None and data.expected_version != draft.content_version:
        raise ValueError("draft_version_conflict")
    normalized = validate_draft(service_request.service_type, data.payload)
    if service_request.service_type == "report":
        normalized["ai_generated_content"] = draft.ai_payload.get("ai_generated_content")
        if "foundation_data" not in normalized:
            normalized["foundation_data"] = draft.ai_payload.get("foundation_data")
    draft.editable_payload = normalized
    draft.content_version += 1
    draft.updated_by = actor.id
    service_request.status = "reviewing"
    service_request.reviewing_at = service_request.reviewing_at or datetime.utcnow()
    service_request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "service_request.draft.save",
        "service_request",
        str(service_request.id),
        target_user_id=service_request.user_id,
        details={"content_version": draft.content_version},
        request=request,
    )
    await db.commit()
    await db.refresh(draft)
    return draft


async def request_more_info(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    data: ServiceRequestInfoInput,
    request: Optional[Request] = None,
) -> ServiceRequest:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    if service_request.status not in {"accepted", "ai_ready", "reviewing", "failed"}:
        raise ValueError("request_info_not_allowed")
    service_request.status = "needs_info"
    service_request.needs_info_reason = data.reason
    service_request.needs_info_at = datetime.utcnow()
    service_request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "service_request.needs_info",
        "service_request",
        str(service_request.id),
        target_user_id=service_request.user_id,
        details={"reason_provided": True},
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request


async def _create_final_report(
    db: AsyncSession,
    service_request: ServiceRequest,
    draft: ServiceRequestDraft,
    actor: User,
) -> Report:
    payload = validate_draft("report", draft.editable_payload)
    request_payload = service_request.request_payload or {}
    profile = request_payload.get("profile") or {}
    birth_date = date(
        int(profile["birth_year"]),
        int(profile["birth_month"]),
        int(profile["birth_day"]),
    )
    birth_time = None
    if profile.get("birth_hour") is not None:
        birth_time = dt_time(int(profile["birth_hour"]), int(profile.get("birth_minute") or 0))
    report = Report(
        user_id=service_request.user_id,
        request_id=service_request.id,
        title=payload.get("title") or "辰鉴·人生说明书",
        birth_date=birth_date,
        birth_time=birth_time,
        birth_calendar_type=profile.get("calendar_type", "solar"),
        birth_place=profile.get("birth_place"),
        input_snapshot={
            "service_type": service_request.service_type,
            "name": profile.get("name") or "用户",
            **deepcopy(request_payload),
        },
        energy_profile=payload["energy_profile"],
        career_guidance=payload["career_guidance"],
        relationship_pattern=payload["relationship_pattern"],
        personal_growth=payload["personal_growth"],
        summary=payload.get("summary"),
        content_payload=payload,
        ai_raw_content=draft.ai_payload.get("ai_generated_content"),
        ai_model=settings.DEEPSEEK_MODEL,
        selected_topics=request_payload.get("selected_topics", []),
        additional_info=request_payload.get("additional_info"),
        reviewed_by=actor.id,
        reviewed_at=datetime.utcnow(),
        status="completed",
        is_deleted=False,
    )
    db.add(report)
    await db.flush()
    return report


async def _create_final_calendar(
    db: AsyncSession,
    service_request: ServiceRequest,
    draft: ServiceRequestDraft,
    actor: User,
) -> UserCalendar:
    payload = validate_draft("calendar", draft.editable_payload)
    current_result = await db.execute(
        select(UserCalendar)
        .where(UserCalendar.user_id == service_request.user_id, UserCalendar.status == "published")
        .order_by(UserCalendar.updated_at.desc())
        .limit(1)
    )
    current = current_result.scalar_one_or_none()
    series_id = current.series_id if current else str(uuid4())
    max_version = await db.scalar(
        select(func.max(UserCalendar.version_number)).where(UserCalendar.series_id == series_id)
    )
    published_calendars = await db.execute(
        select(UserCalendar).where(
            UserCalendar.user_id == service_request.user_id,
            UserCalendar.status == "published",
        )
    )
    for old_calendar in published_calendars.scalars().all():
        old_calendar.status = "archived"
        old_calendar.updated_by = actor.id

    calendar = UserCalendar(
        user_id=service_request.user_id,
        request_id=service_request.id,
        series_id=series_id,
        version_number=(max_version or 0) + 1,
        title=payload["title"],
        start_date=date.fromisoformat(payload["start_date"]),
        end_date=date.fromisoformat(payload["end_date"]),
        status="published",
        meta_payload=payload.get("meta_payload") or {},
        created_by=actor.id,
        updated_by=actor.id,
        published_at=datetime.utcnow(),
    )
    db.add(calendar)
    await db.flush()
    for raw_entry in payload["entries"]:
        entry = CalendarEntryInput.model_validate(raw_entry)
        db.add(CalendarEntry(calendar_id=calendar.id, **entry.model_dump()))
    await db.flush()
    return calendar


async def deliver_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    request: Optional[Request] = None,
) -> ServiceRequest:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    if service_request.status == "delivered":
        return service_request
    if service_request.status not in {"ai_ready", "reviewing"}:
        raise ValueError("service_request_delivery_not_allowed")
    locked = await _get_request_for_update(db, service_request.id)
    if locked is None:
        raise ValueError("service_request_not_found")
    if locked.status == "delivered":
        return locked
    draft = await _get_draft(db, locked.id)
    if draft is None:
        raise ValueError("service_request_draft_not_found")
    if locked.service_type == "report":
        result = await _create_final_report(db, locked, draft, actor)
        result_type = "report"
    else:
        result = await _create_final_calendar(db, locked, draft, actor)
        result_type = "calendar"
    locked.status = "delivered"
    locked.result_type = result_type
    locked.result_id = result.id
    locked.delivered_at = datetime.utcnow()
    locked.updated_by = actor.id
    await _append_revision(db, locked.id, "delivered", draft.editable_payload, actor.id)
    await record_audit(
        db,
        actor.id,
        "service_request.deliver",
        "service_request",
        str(locked.id),
        target_user_id=locked.user_id,
        details={"result_type": result_type, "result_id": result.id},
        request=request,
    )
    await db.commit()
    await db.refresh(locked)
    return locked
