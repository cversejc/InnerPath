"""AI draft, review, and final delivery workflow."""

from copy import deepcopy
from datetime import date, datetime, time as dt_time
from typing import Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.calendar import CalendarEntry, UserCalendar
from app.models.report import Report
from app.models.service_request import ServiceRequest, ServiceRequestDraft, ServiceRequestTask
from app.models.user import User
from app.schemas.calendar import CalendarEntryInput
from app.schemas.service_request import ServiceRequestDraftUpdate, ServiceRequestInfoInput
from app.services.audit_service import record_audit
from app.services.service_request_payloads import validate_draft
from app.services.service_request_repository import (
    _append_revision,
    _get_draft,
    _get_draft_for_update,
    _get_latest_task,
    _get_request_for_update,
)
from app.services.service_request_staff import staff_can_access


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
