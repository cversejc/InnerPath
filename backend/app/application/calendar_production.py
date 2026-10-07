"""User submission and worker orchestration for report-based calendars."""
from datetime import datetime, timedelta
from app.core.time import utc_now_naive, utc_now_iso
from sqlalchemy import select

from app.domains.calendar.models import CalendarRequest
from app.domains.calendar.requests import create_calendar_request
from app.domains.calendar.production import freeze_calendar_skills, produce_calendar
from app.domains.calendar.service import create_ai_calendar_for_request
from app.domains.workflow.service import enqueue_outbox_event
from app.models.user import User
from app.domains.audit.service import record_audit
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.examples import retrieve_skill_examples


async def recover_stalled_calendar_requests(db):
    # Longer than the worker hard limit: a live task cannot still publish.
    cutoff = utc_now_naive() - timedelta(minutes=45)
    rows = await db.scalars(select(CalendarRequest).where(CalendarRequest.status == "generating",
        CalendarRequest.updated_at < cutoff).with_for_update(skip_locked=True))
    count = 0
    for request in rows:
        snapshot = dict(request.input_snapshot or {})
        snapshot["generation"] = {**snapshot.get("generation", {}), "status": "FAILED",
                                  "error_code": "calendar_worker_interrupted"}
        request.input_snapshot, request.status = snapshot, "failed"
        interrupted_runs = await db.scalars(select(SkillRun).where(
            SkillRun.target_type == "CALENDAR_PRODUCTION", SkillRun.target_key == str(request.id),
            SkillRun.status.in_({"PENDING", "RUNNING"})).with_for_update())
        for run in interrupted_runs:
            run.status, run.error, run.completed_at = "FAILED", "calendar_worker_interrupted", utc_now_naive()
        await record_audit(db, request.user_id, "calendar.ai.interrupted", "calendar_request", str(request.id),
                           target_user_id=request.user_id, details={"recovery": "retry_available"})
        count += 1
    return count


async def queue_calendar_from_report(db, user, data, *, audit_context=None):
    # Serialize repeated submissions from the same account, including page reloads.
    await db.scalar(select(User).where(User.id == user.id).with_for_update())
    existing = await db.scalar(select(CalendarRequest).where(
        CalendarRequest.user_id == user.id, CalendarRequest.source_report_id == data.source_report_id,
        CalendarRequest.start_date == data.start_date, CalendarRequest.end_date == data.end_date,
        CalendarRequest.status.in_({"queued", "generating"}),
    ).order_by(CalendarRequest.id.desc()).limit(1))
    if existing:
        return existing
    request = await create_calendar_request(db, user, data, audit_context, commit=False)
    request.status = "queued"
    bindings = await freeze_calendar_skills(db)
    examples = {}
    for key, binding in bindings.items():
        version = await db.get(AISkillVersion, binding["id"])
        policy = version.specification_json.get("example_policy") or {}
        examples[key] = await retrieve_skill_examples(db, skill_key=key, target_key=None,
            context={"focus_topics": data.focus_topics, "usage_scenario": data.usage_scenario},
            max_examples=policy.get("max_examples", 3) if policy.get("enabled") else 0)
    request.input_snapshot = {**request.input_snapshot, "calendar_skill_bindings": bindings, "calendar_examples": examples,
                              "generation": {"status": "QUEUED", "attempt": 1, "completed_runs": 0, "total_runs": 8}}
    await enqueue_outbox_event(db, aggregate_type="calendar_request", aggregate_id=request.id,
        event_type="calendar.generation.requested", payload={"calendar_request_id": request.id, "attempt": 1})
    await db.commit()
    await db.refresh(request)
    return request


async def retry_calendar_production(db, user, request_id):
    request = await db.scalar(select(CalendarRequest).where(CalendarRequest.id == request_id,
                        CalendarRequest.user_id == user.id).with_for_update())
    if request is None:
        raise ValueError("calendar_request_not_found")
    if request.status != "failed":
        raise ValueError("calendar_request_not_failed")
    snapshot = dict(request.input_snapshot or {})
    attempt = snapshot.get("generation", {}).get("attempt", 1) + 1
    snapshot["generation"] = {"status": "QUEUED", "attempt": attempt, "completed_runs": 0, "total_runs": 8}
    request.input_snapshot, request.status = snapshot, "queued"
    await enqueue_outbox_event(db, aggregate_type="calendar_request", aggregate_id=request.id,
        event_type="calendar.generation.requested", payload={"calendar_request_id": request.id, "attempt": attempt})
    await db.commit()
    return request


async def execute_calendar_production(db, request_id, attempt, *, gateway=None):
    request = await db.scalar(select(CalendarRequest).where(CalendarRequest.id == request_id).with_for_update())
    if request is None:
        return {"status": "missing"}
    generation = (request.input_snapshot or {}).get("generation") or {}
    if generation.get("attempt", 1) != attempt or request.status in {"fulfilled", "cancelled", "rejected", "failed"}:
        return {"status": "stale"}
    if request.status == "generating":
        return {"status": "running"}
    request.status = "generating"
    request.input_snapshot = {**request.input_snapshot, "generation": {**generation,
        "status": "RUNNING", "started_at": utc_now_iso()}}
    await db.commit()
    try:
        data = await produce_calendar(db, request, gateway=gateway)
        await create_ai_calendar_for_request(db, calendar_request=request, user_id=request.user_id,
                                            created_by=request.user_id, data=data)
        return {"status": "fulfilled", "request_id": request.id}
    except Exception as error:
        await db.rollback()
        request = await db.get(CalendarRequest, request_id)
        snapshot = dict(request.input_snapshot or {})
        snapshot["generation"] = {**snapshot.get("generation", {}), "status": "FAILED",
            "attempt": attempt, "error_code": str(error) if isinstance(error, ValueError) else "calendar_ai_generation_failed"}
        request.input_snapshot, request.status = snapshot, "failed"
        await record_audit(db, request.user_id, "calendar.ai.failed", "calendar_request", str(request.id),
                           target_user_id=request.user_id, details={"failure_type": type(error).__name__})
        await db.commit()
        return {"status": "failed", "request_id": request.id}
