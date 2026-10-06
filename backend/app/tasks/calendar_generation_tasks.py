import asyncio
from copy import deepcopy
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from app.core.cache import close_redis
from app.core.logging_config import get_logger
from app.db.session import AsyncSessionLocal, engine
from app.domains.audit.service import record_audit
from app.domains.calendar.generation import generate_calendar_with_ai
from app.domains.calendar.models import CalendarEntry, CalendarRequest, UserCalendar
from app.domains.calendar.requests import get_delivered_source_report
from app.domains.calendar.schemas import CalendarEntryInput
from app.domains.reports.models import Report
from app.domains.service_requests.drafts import validate_draft
from app.models.user import User  # noqa: F401 - registers user foreign keys in the worker process
from app.tasks.celery_app import celery_app


logger = get_logger(__name__)


def _generation_input(calendar_request: CalendarRequest, report: Report) -> dict[str, Any]:
    snapshot = calendar_request.input_snapshot or {}
    profile = deepcopy(snapshot.get("profile") or {})
    report_snapshot = report.input_snapshot or {}
    report_content = report.content_payload or {}
    return {
        **profile,
        "source_report": {
            "id": report.id,
            "title": report.title,
            "summary": report.summary,
            "energy_profile": report.energy_profile or {},
            "career_guidance": report.career_guidance or {},
            "relationship_pattern": report.relationship_pattern or {},
            "personal_growth": report.personal_growth or {},
            "foundation_data": report_content.get("foundation_data"),
            "report_context": report_snapshot.get("context") or {},
        },
        "source_report_id": report.id,
        "start_date": calendar_request.start_date.isoformat(),
        "end_date": calendar_request.end_date.isoformat(),
        "selected_topics": calendar_request.focus_topics or [],
        "calendar_goal": calendar_request.goal,
        "usage_scenario": calendar_request.usage_scenario,
        "expected_outcomes": calendar_request.expected_outcomes or [],
        "decision_description": calendar_request.decision_description,
        "additional_info": calendar_request.additional_info,
    }


async def _run_calendar_generation(task_id: str, request_id: int) -> dict[str, Any]:
    try:
        async with AsyncSessionLocal() as db:
            calendar_request = await db.get(CalendarRequest, request_id)
            if not calendar_request or calendar_request.task_id != task_id:
                return {"status": "superseded", "request_id": request_id}
            if calendar_request.status != "processing":
                return {"status": calendar_request.status, "request_id": request_id}
            source_report = await get_delivered_source_report(
                db, calendar_request.user_id, calendar_request.source_report_id
            )
            if source_report is None:
                raise ValueError("calendar_request_source_report_not_delivered")
            user_data = _generation_input(calendar_request, source_report)
            calendar_request.progress = 10
            await db.commit()

        ai_payload = await generate_calendar_with_ai(user_data)
        ai_payload["start_date"] = user_data["start_date"]
        ai_payload["end_date"] = user_data["end_date"]
        validated = validate_draft("calendar", ai_payload)

        async with AsyncSessionLocal() as db:
            calendar_request = await db.scalar(
                select(CalendarRequest)
                .where(CalendarRequest.id == request_id)
                .with_for_update()
            )
            if not calendar_request or calendar_request.task_id != task_id:
                return {"status": "superseded", "request_id": request_id}
            if calendar_request.status != "processing":
                return {"status": calendar_request.status, "request_id": request_id}

            # Serializing publication on the user row prevents competing requests
            # from leaving multiple calendars active at the same time.
            user = await db.scalar(
                select(User)
                .where(User.id == calendar_request.user_id)
                .with_for_update()
            )
            if user is None:
                raise ValueError("calendar_request_user_not_found")
            source_report = await get_delivered_source_report(
                db, calendar_request.user_id, calendar_request.source_report_id
            )
            if source_report is None:
                raise ValueError("calendar_request_source_report_not_delivered")

            published = await db.execute(
                select(UserCalendar)
                .where(
                    UserCalendar.user_id == calendar_request.user_id,
                    UserCalendar.status == "published",
                )
                .order_by(UserCalendar.updated_at.desc())
                .with_for_update()
            )
            previous_calendars = list(published.scalars().all())
            current = previous_calendars[0] if previous_calendars else None
            series_id = current.series_id if current else str(uuid4())
            max_version = await db.scalar(
                select(func.max(UserCalendar.version_number)).where(
                    UserCalendar.series_id == series_id
                )
            )
            for previous in previous_calendars:
                previous.status = "archived"
            await db.flush()

            calendar = UserCalendar(
                user_id=calendar_request.user_id,
                series_id=series_id,
                version_number=(max_version or 0) + 1,
                title=validated["title"],
                start_date=date.fromisoformat(validated["start_date"]),
                end_date=date.fromisoformat(validated["end_date"]),
                status="published",
                meta_payload=validated.get("meta_payload") or {},
                created_by=calendar_request.user_id,
                updated_by=calendar_request.user_id,
                published_at=datetime.utcnow(),
                calendar_request_id=calendar_request.id,
                source_report_id=calendar_request.source_report_id,
            )
            db.add(calendar)
            await db.flush()
            for raw_entry in validated["entries"]:
                entry = CalendarEntryInput.model_validate(raw_entry)
                db.add(
                    CalendarEntry(
                        calendar_id=calendar.id,
                        **entry.model_dump(exclude={"admin_note"}),
                        admin_note=None,
                    )
                )
            calendar_request.status = "delivered"
            calendar_request.progress = 100
            calendar_request.generation_error = None
            await record_audit(
                db,
                None,
                "calendar.generation.completed",
                "calendar_request",
                str(calendar_request.id),
                target_user_id=calendar_request.user_id,
                details={"calendar_id": calendar.id, "source_report_id": source_report.id},
            )
            await db.commit()
            return {
                "status": "delivered",
                "request_id": calendar_request.id,
                "calendar_id": calendar.id,
            }
    except Exception as error:
        logger.exception("决策日历生成失败 | task_id=%s | request_id=%s", task_id, request_id)
        try:
            async with AsyncSessionLocal() as db:
                calendar_request = await db.get(CalendarRequest, request_id)
                if calendar_request and calendar_request.task_id == task_id:
                    calendar_request.status = "failed"
                    calendar_request.progress = 0
                    calendar_request.generation_error = str(error)
                    await record_audit(
                        db,
                        None,
                        "calendar.generation.failed",
                        "calendar_request",
                        str(calendar_request.id),
                        target_user_id=calendar_request.user_id,
                        details={"error_type": type(error).__name__},
                    )
                    await db.commit()
        except Exception:
            logger.exception(
                "决策日历失败状态保存失败 | task_id=%s | request_id=%s",
                task_id,
                request_id,
            )
        raise
    finally:
        try:
            await engine.dispose()
        except Exception:
            logger.exception("日历任务数据库连接释放失败 | task_id=%s", task_id)
        try:
            await close_redis()
        except Exception:
            logger.exception("日历任务 Redis 连接释放失败 | task_id=%s", task_id)


@celery_app.task(bind=True, name="generate_calendar_from_report")
def generate_calendar_from_report_task(self, request_id: int):
    return asyncio.run(_run_calendar_generation(self.request.id, request_id))
