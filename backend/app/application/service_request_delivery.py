"""Create and deliver final report or calendar artifacts."""

from datetime import date, datetime
from app.core.time import utc_now_naive
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import CalendarEntry, UserCalendar
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
from app.application.report_delivery import deliver_report_case
from app.application.report_cases import get_report_case_for_service_request


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
        published_at=utc_now_naive(),
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
    locked = await _get_request_for_update(db, service_request.id)
    if locked is None:
        raise ValueError("service_request_not_found")
    if locked.service_type == "report":
        report_case = await get_report_case_for_service_request(db, locked.id)
        if report_case is None:
            raise ValueError("report_case_workflow_required")
        await deliver_report_case(
            db,
            report_case=report_case,
            actor=actor,
            audit_context=audit_context,
        )
        await db.refresh(locked)
        return locked
    if locked.status == "delivered":
        return locked
    if locked.status not in {"ai_ready", "reviewing"}:
        raise ValueError("service_request_delivery_not_allowed")
    draft = await _get_draft(db, locked.id)
    if draft is None:
        raise ValueError("service_request_draft_not_found")
    result = await _create_final_calendar(db, locked, draft, actor)
    result_type = "calendar"
    locked.status = "delivered"
    locked.result_type = result_type
    locked.result_id = result.id
    locked.delivered_at = utc_now_naive()
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
