from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.calendar.generation import (
    generate_calendar_with_ai,
    validate_generated_calendar,
)
from app.domains.calendar.models import CalendarRequest
from app.domains.calendar.requests import create_calendar_request
from app.domains.calendar.schemas import CalendarRequestCreate
from app.domains.calendar.service import create_ai_calendar_for_request
from app.models.user import User


logger = get_logger(__name__)


def _calendar_ai_input(calendar_request: CalendarRequest) -> dict[str, Any]:
    snapshot = calendar_request.input_snapshot or {}
    profile = snapshot.get("profile") or {}
    return {
        **profile,
        "start_date": calendar_request.start_date.isoformat(),
        "end_date": calendar_request.end_date.isoformat(),
        "selected_topics": calendar_request.focus_topics or [],
        "usage_scenario": calendar_request.usage_scenario,
        "calendar_goal": calendar_request.goal,
        "decision_description": calendar_request.decision_description,
        "expected_outcomes": calendar_request.expected_outcomes or [],
        "additional_info": calendar_request.additional_info,
        "source_report": snapshot.get("source_report") or {},
    }


async def generate_calendar_from_report(
    db: AsyncSession,
    user: User,
    data: CalendarRequestCreate,
    *,
    audit_context: AuditContext | None = None,
) -> CalendarRequest:
    calendar_request = await create_calendar_request(
        db, user, data, audit_context=audit_context
    )

    try:
        ai_input = _calendar_ai_input(calendar_request)
        ai_output = await generate_calendar_with_ai(ai_input)
        calendar_data = validate_generated_calendar(ai_output, ai_input)
        await create_ai_calendar_for_request(
            db,
            calendar_request=calendar_request,
            user_id=user.id,
            created_by=user.id,
            data=calendar_data,
            audit_context=audit_context,
        )
        return calendar_request
    except Exception as error:
        logger.exception(
            "AI 日历生成或交付失败 | request_id=%s", calendar_request.id
        )
        await db.rollback()
        failed_request = await db.get(CalendarRequest, calendar_request.id)
        if failed_request is not None:
            snapshot = dict(failed_request.input_snapshot or {})
            snapshot["generation"] = {
                "status": "FAILED",
                "error_code": "calendar_ai_generation_failed",
                "failure_type": type(error).__name__,
            }
            failed_request.input_snapshot = snapshot
            failed_request.status = "failed"
            await record_audit(
                db,
                user.id,
                "calendar.ai.failed",
                "calendar_request",
                str(failed_request.id),
                target_user_id=user.id,
                details={"source_report_id": failed_request.source_report_id},
                audit_context=audit_context,
            )
            await db.commit()
        raise ValueError("calendar_ai_generation_failed") from error
