from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import CalendarRequest, UserCalendar
from app.domains.reports.models import Report
from app.models.user import User
from app.domains.calendar.schemas import CalendarRequestAdminUpdate, CalendarRequestCreate
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.services.intake_service import build_intake_snapshot

def _calendar_request_context(data: CalendarRequestCreate) -> dict:
    return {
        "focus_topics": data.focus_topics,
        "current_challenge": data.goal,
        "expected_outcomes": data.expected_outcomes,
        "decision_description": data.decision_description,
        "additional_info": data.additional_info,
    }


async def create_calendar_request(
    db: AsyncSession,
    user: User,
    data: CalendarRequestCreate,
    audit_context: Optional[AuditContext] = None,
) -> CalendarRequest:
    """Create a user-owned calendar request with an immutable profile snapshot."""
    if user.profile_completion < 100:
        raise ValueError("calendar_request_profile_incomplete")
    if data.start_date is None or data.end_date is None:
        raise ValueError("calendar_request_requires_date_range")
    if data.start_date > data.end_date:
        raise ValueError("invalid_calendar_range")
    if (data.end_date - data.start_date).days != 29:
        raise ValueError("calendar_request_requires_30_days")
    if not data.focus_topics:
        raise ValueError("calendar_request_requires_focus_topics")
    if not data.usage_scenario:
        raise ValueError("calendar_request_requires_usage_scenario")
    if not data.goal or not data.goal.strip():
        raise ValueError("calendar_request_requires_goal")
    if not data.expected_outcomes:
        raise ValueError("calendar_request_requires_expected_outcomes")
    if data.source_report_id is None:
        raise ValueError("calendar_request_requires_source_report")
    source_report = await db.scalar(
        select(Report).where(
            Report.id == data.source_report_id,
            Report.user_id == user.id,
            Report.status == "completed",
            Report.is_deleted.is_(False),
        )
    )
    if source_report is None:
        raise ValueError("calendar_request_source_report_mismatch")

    report_content = source_report.content_payload or {}
    source_report_snapshot = {
        "id": source_report.id,
        "title": source_report.title,
        "summary": report_content.get("summary") or source_report.summary,
        "structured_sections": report_content.get("structured_sections") or [],
        "energy_profile": report_content.get("energy_profile") or source_report.energy_profile,
        "career_guidance": report_content.get("career_guidance") or source_report.career_guidance,
        "relationship_pattern": report_content.get("relationship_pattern") or source_report.relationship_pattern,
        "personal_growth": report_content.get("personal_growth") or source_report.personal_growth,
    }

    snapshot = build_intake_snapshot(
        user,
        _calendar_request_context(data),
        request_type="calendar",
        profile_version=data.profile_version,
        source_report_id=data.source_report_id,
        extra={
            "calendar": {
                "start_date": data.start_date.isoformat(),
                "end_date": data.end_date.isoformat(),
                "usage_scenario": data.usage_scenario,
            }
        },
    )
    snapshot["source_report"] = source_report_snapshot
    snapshot["generation"] = {"status": "RUNNING"}
    calendar_request = CalendarRequest(
        user_id=user.id,
        source_report_id=data.source_report_id,
        profile_version=snapshot["profile_version"],
        start_date=data.start_date,
        end_date=data.end_date,
        focus_topics=data.focus_topics,
        usage_scenario=data.usage_scenario,
        goal=data.goal.strip(),
        decision_description=(data.decision_description or "").strip() or None,
        expected_outcomes=data.expected_outcomes,
        additional_info=(data.additional_info or "").strip() or None,
        status="generating",
        input_snapshot=snapshot,
    )
    db.add(calendar_request)
    await db.flush()
    await record_audit(
        db,
        user.id,
        "calendar.request.create",
        "calendar_request",
        str(calendar_request.id),
        target_user_id=user.id,
        details={
            "profile_version": calendar_request.profile_version,
            "focus_topics": calendar_request.focus_topics,
        },
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar_request)
    return calendar_request


async def _linked_calendar_id(db: AsyncSession, request_id: int) -> Optional[int]:
    return await db.scalar(
        select(UserCalendar.id)
        .where(UserCalendar.calendar_request_id == request_id)
        .order_by(UserCalendar.updated_at.desc())
        .limit(1)
    )


async def serialize_calendar_request(db: AsyncSession, calendar_request: CalendarRequest) -> dict:
    return {
        "id": calendar_request.id,
        "user_id": calendar_request.user_id,
        "profile_version": calendar_request.profile_version,
        "start_date": calendar_request.start_date,
        "end_date": calendar_request.end_date,
        "focus_topics": calendar_request.focus_topics or [],
        "usage_scenario": calendar_request.usage_scenario,
        "goal": calendar_request.goal,
        "decision_description": calendar_request.decision_description,
        "expected_outcomes": calendar_request.expected_outcomes or [],
        "additional_info": calendar_request.additional_info,
        "status": calendar_request.status,
        "source_report_id": calendar_request.source_report_id,
        "calendar_id": await _linked_calendar_id(db, calendar_request.id),
        "reviewer_id": calendar_request.reviewer_id,
        "reviewed_at": calendar_request.reviewed_at,
        "review_note": calendar_request.review_note,
        "generation_error": (calendar_request.input_snapshot or {}).get("generation", {}).get("error_code"),
        "created_at": calendar_request.created_at,
        "updated_at": calendar_request.updated_at,
    }


async def get_user_calendar_requests(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
) -> list[dict]:
    result = await db.execute(
        select(CalendarRequest)
        .where(CalendarRequest.user_id == user_id)
        .order_by(CalendarRequest.created_at.desc())
        .limit(limit)
    )
    return [await serialize_calendar_request(db, item) for item in result.scalars().all()]


async def get_calendar_requests_for_admin(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
) -> list[dict]:
    query = select(CalendarRequest).order_by(CalendarRequest.created_at.desc()).limit(limit)
    if status_filter:
        query = query.where(CalendarRequest.status == status_filter)
    if user_id:
        query = query.where(CalendarRequest.user_id == user_id)
    result = await db.execute(query)
    return [await serialize_calendar_request(db, item) for item in result.scalars().all()]


async def update_calendar_request(
    db: AsyncSession,
    calendar_request: CalendarRequest,
    reviewer_id: int,
    data: CalendarRequestAdminUpdate,
    audit_context: Optional[AuditContext] = None,
) -> dict:
    if "calendar_id" in data.model_fields_set:
        linked_calendars = list(
            (
                await db.execute(
                    select(UserCalendar).where(UserCalendar.calendar_request_id == calendar_request.id)
                )
            ).scalars().all()
        )
        if data.calendar_id is not None:
            calendar = await db.get(UserCalendar, data.calendar_id)
            if not calendar or calendar.user_id != calendar_request.user_id:
                raise ValueError("calendar_request_calendar_mismatch")
            for linked_calendar in linked_calendars:
                if linked_calendar.id != calendar.id:
                    linked_calendar.calendar_request_id = None
            calendar.calendar_request_id = calendar_request.id
        else:
            for linked_calendar in linked_calendars:
                linked_calendar.calendar_request_id = None

    calendar_request.status = data.status
    calendar_request.review_note = (data.review_note or "").strip() or None
    calendar_request.reviewer_id = reviewer_id
    calendar_request.reviewed_at = datetime.utcnow()
    await record_audit(
        db,
        reviewer_id,
        "calendar.request.update",
        "calendar_request",
        str(calendar_request.id),
        target_user_id=calendar_request.user_id,
        details={
            "status": calendar_request.status,
            "calendar_id": data.calendar_id,
        },
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar_request)
    return await serialize_calendar_request(db, calendar_request)
