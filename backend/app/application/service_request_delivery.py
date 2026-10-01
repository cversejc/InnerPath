"""Create and deliver final report or calendar artifacts."""

from copy import deepcopy
from datetime import date, datetime, time as dt_time
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.calendar.models import CalendarEntry, UserCalendar
from app.domains.reports.models import Report
from app.domains.service_requests.models import ServiceRequest, ServiceRequestDraft
from app.models.user import User
from app.domains.calendar.schemas import CalendarEntryInput
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.service_requests.drafts import validate_draft
from app.domains.service_requests.repository import (
    _append_revision,
    _get_draft,
    _get_request_for_update,
)
from app.domains.service_requests.staff import staff_can_access


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
    audit_context: Optional[AuditContext] = None,
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
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(locked)
    return locked
