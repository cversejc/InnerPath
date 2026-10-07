from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import CalendarRequest, UserCalendar, DecisionLog
from app.domains.calendar.practices import project_report_practices
from app.domains.reports.models import Report
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.domains.calendar.schemas import CalendarRequestAdminUpdate, CalendarRequestCreate
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.services.intake_service import build_intake_snapshot
from app.core.time import utc_now_naive, utc_naive_for_shanghai_date
from app.domains.delivery.models import ReportVersion
from copy import deepcopy


async def get_delivered_source_report(
    db: AsyncSession, user_id: int, report_id: int
) -> Optional[Report]:
    """Return only reports delivered to this user through consultant review."""
    return await db.scalar(
        select(Report)
        .join(
            ServiceRequest,
            (ServiceRequest.id == Report.request_id)
            & (ServiceRequest.result_id == Report.id),
        )
        .where(
            Report.id == report_id,
            Report.user_id == user_id,
            Report.status == "completed",
            Report.is_deleted.is_(False),
            Report.reviewed_at.is_not(None),
            ServiceRequest.user_id == user_id,
            ServiceRequest.service_type == "report",
            ServiceRequest.status == "delivered",
            ServiceRequest.result_type == "report",
        )
    )

def _calendar_request_context(data: CalendarRequestCreate) -> dict:
    return {
        "focus_topics": data.focus_topics,
        "current_challenge": data.goal,
        "expected_outcomes": data.expected_outcomes,
        "decision_description": data.decision_description,
        "additional_info": data.additional_info,
        "available_minutes_per_day": data.available_minutes_per_day,
    }


async def create_calendar_request(
    db: AsyncSession,
    user: User,
    data: CalendarRequestCreate,
    audit_context: Optional[AuditContext] = None,
    *, commit: bool = True,
) -> CalendarRequest:
    """Create a user-owned calendar request with an immutable profile snapshot."""
    if user.profile_completion < 100:
        raise ValueError("calendar_request_profile_incomplete")
    if data.start_date is None or data.end_date is None:
        raise ValueError("calendar_request_requires_date_range")
    if data.start_date > data.end_date:
        raise ValueError("invalid_calendar_range")
    if (data.end_date - data.start_date).days != 29:
        raise ValueError("calendar_request_must_cover_30_days")
    if not data.focus_topics:
        raise ValueError("calendar_request_requires_focus_topics")
    if not data.usage_scenario:
        raise ValueError("calendar_request_requires_usage_scenario")
    if not data.goal or not data.goal.strip():
        raise ValueError("calendar_request_requires_goal")
    if not data.expected_outcomes:
        raise ValueError("calendar_request_requires_expected_outcomes")
    if data.source_report_id is None:
        raise ValueError("calendar_request_source_report_required")
    source_report = await get_delivered_source_report(db, user.id, data.source_report_id)
    if source_report is None:
        raise ValueError("calendar_request_source_report_not_delivered")

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
    version_id = (source_report.input_snapshot or {}).get("report_version", {}).get("id")
    if version_id is not None:
        version = await db.get(ReportVersion, version_id)
        if version is None:
            raise ValueError("calendar_source_version_missing")
        from app.domains.workflow.models import ReportCase
        source_case = await db.get(ReportCase, version.report_case_id)
        if source_case is None or source_case.user_id != user.id or source_case.status != "DELIVERED":
            raise ValueError("calendar_request_source_report_mismatch")
        semantics = (version.semantic_snapshot or {}).get("semantics") or {}
        evidence = semantics.get("evidence") or []
        foundation_rows = [
            e for e in evidence
            if e.get("source_type") in {"CONSULTANT_CORRECTED", "SYSTEM_CALCULATED"}
            and isinstance(e.get("value"), dict)
            and e["value"].get("bazi")
        ]
        foundation_rows.sort(key=lambda e: (
            0 if e.get("source_type") == "CONSULTANT_CORRECTED"
            and str(e.get("evidence_key", "")).startswith("calculated.mingli_foundation.consultant.")
            else 1 if e.get("source_type") == "SYSTEM_CALCULATED"
            and str(e.get("evidence_key", "")).startswith("calculated.mingli_foundation.v2")
            else 2
        ))
        foundation = foundation_rows[0].get("value") if foundation_rows else {}
        source_report_snapshot.update({
            "report_version_id": version.id, "report_case_id": version.report_case_id,
            "summary": (version.structured_data.get("narrative_plan") or {}).get("core_theme"),
            "structured_sections": deepcopy(version.structured_data.get("structured_sections") or []),
            "confirmed_semantics": deepcopy(semantics), "reviewed_foundation": deepcopy(foundation),
            "application": deepcopy((version.semantic_snapshot or {}).get("application_snapshot") or {}),
            "practice_rhythm": project_report_practices(semantics, version.id),
        })
    else:
        # Legacy delivered reports remain useful for growth prompts. No re-charting.
        source_report_snapshot["reviewed_foundation"] = deepcopy(report_content.get("mingli_foundation") or {})
        source_report_snapshot["application"] = deepcopy(source_report.input_snapshot or {})

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
                "available_minutes_per_day": data.available_minutes_per_day,
            }
        },
    )
    snapshot["source_report"] = source_report_snapshot
    snapshot["available_minutes_per_day"] = data.available_minutes_per_day
    feedback = await db.scalars(select(DecisionLog).where(DecisionLog.user_id == user.id,
        DecisionLog.log_date < data.start_date).order_by(DecisionLog.log_date.desc(), DecisionLog.id.desc()).limit(30))
    snapshot["decision_feedback"] = [{"log_date": row.log_date.isoformat(), "kind": row.kind,
        "status": row.status, "content": row.content, "note": row.note} for row in feedback]
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
        status="processing",
        task_id=str(uuid4()),
        progress=0,
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
    if commit:
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
        "available_minutes_per_day": (calendar_request.input_snapshot or {}).get(
            "available_minutes_per_day", 30
        ),
        "status": calendar_request.status,
        "source_report_id": calendar_request.source_report_id,
        "task_id": calendar_request.task_id,
        "progress": calendar_request.progress,
        "retry_count": calendar_request.retry_count,
        "input_snapshot": calendar_request.input_snapshot,
        "calendar_id": await _linked_calendar_id(db, calendar_request.id),
        "reviewer_id": calendar_request.reviewer_id,
        "reviewed_at": calendar_request.reviewed_at,
        "review_note": calendar_request.review_note,
        "generation_error": calendar_request.generation_error
        or (calendar_request.input_snapshot or {}).get("generation", {}).get("error_code"),
        "generation_stage": (calendar_request.input_snapshot or {}).get("generation", {}).get("stage"),
        "completed_runs": (calendar_request.input_snapshot or {}).get("generation", {}).get("completed_runs", 0),
        "total_runs": (calendar_request.input_snapshot or {}).get("generation", {}).get("total_runs", 8),
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
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    stalled_only: bool = False,
    page: int = 1,
    size: int = 20,
) -> dict:
    conditions = []
    if status_filter:
        conditions.append(CalendarRequest.status == status_filter)
    if stalled_only:
        conditions.extend((
            CalendarRequest.status == "generating",
            CalendarRequest.updated_at < datetime.utcnow() - timedelta(minutes=45),
        ))
    if user_id:
        conditions.append(CalendarRequest.user_id == user_id)
    if date_from:
        conditions.append(CalendarRequest.created_at >= utc_naive_for_shanghai_date(date_from))
    if date_to:
        conditions.append(CalendarRequest.created_at < utc_naive_for_shanghai_date(date_to, end=True))
    if search:
        term = f"%{search.strip()}%"
        conditions.append(or_(User.name.ilike(term), User.phone.ilike(term)))

    count_query = select(func.count(CalendarRequest.id)).join(User, User.id == CalendarRequest.user_id)
    query = select(CalendarRequest, User).join(User, User.id == CalendarRequest.user_id)
    if conditions:
        count_query = count_query.where(*conditions)
        query = query.where(*conditions)
    total = int(await db.scalar(count_query) or 0)
    result = await db.execute(
        query.order_by(CalendarRequest.created_at.desc(), CalendarRequest.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = []
    for item, user in result.all():
        serialized = await serialize_calendar_request(db, item)
        serialized["user_name"] = user.name
        serialized["user_phone"] = user.phone
        items.append(serialized)
    return {"total": total, "page": page, "size": size, "items": items}


async def retry_calendar_generation(
    db: AsyncSession,
    calendar_request: CalendarRequest,
    user: User,
    audit_context: Optional[AuditContext] = None,
) -> CalendarRequest:
    if calendar_request.user_id != user.id:
        raise ValueError("calendar_request_not_found")
    if calendar_request.status != "failed":
        raise ValueError("calendar_request_retry_not_allowed")
    if await get_delivered_source_report(db, user.id, calendar_request.source_report_id) is None:
        raise ValueError("calendar_request_source_report_not_delivered")
    calendar_request.status = "processing"
    calendar_request.task_id = str(uuid4())
    calendar_request.progress = 0
    calendar_request.generation_error = None
    calendar_request.retry_count = (calendar_request.retry_count or 0) + 1
    await record_audit(
        db,
        user.id,
        "calendar.generation.retry",
        "calendar_request",
        str(calendar_request.id),
        target_user_id=user.id,
        details={"source_report_id": calendar_request.source_report_id},
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(calendar_request)
    return calendar_request


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
    calendar_request.reviewed_at = utc_now_naive()
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
