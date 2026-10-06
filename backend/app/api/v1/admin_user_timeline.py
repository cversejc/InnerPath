from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.audit.models import AuditLog
from app.domains.calendar.models import CalendarRequest, DecisionLog, UserCalendar
from app.domains.reports.models import Report, ReportTask
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.schemas.admin import AdminUserTimelineResponse
from app.api.v1.admin_user_timeline_support import build_admin_user_timeline

router = APIRouter()


@router.get("/users/{user_id}/timeline", response_model=AdminUserTimelineResponse)
async def get_admin_user_timeline(
    user_id: int,
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    async def recent(model, *conditions):
        statement = select(model).where(*conditions).order_by(model.created_at.desc()).limit(100)
        return (await db.scalars(statement)).all()

    service_requests = await recent(ServiceRequest, ServiceRequest.user_id == user_id)
    calendar_requests = await recent(CalendarRequest, CalendarRequest.user_id == user_id)
    reports = await recent(Report, Report.user_id == user_id, Report.is_deleted.is_(False))
    report_tasks = await recent(ReportTask, ReportTask.user_id == user_id)
    calendars = await recent(UserCalendar, UserCalendar.user_id == user_id)
    decision_logs = await recent(DecisionLog, DecisionLog.user_id == user_id)
    audit_entries = (await db.execute(
        select(AuditLog, User.name)
        .outerjoin(User, AuditLog.actor_user_id == User.id)
        .where(AuditLog.target_user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )).all()

    return AdminUserTimelineResponse(
        user_id=user_id,
        items=build_admin_user_timeline(
            user_created_at=user.created_at,
            service_requests=service_requests,
            calendar_requests=calendar_requests,
            reports=reports,
            report_tasks=report_tasks,
            calendars=calendars,
            decision_logs=decision_logs,
            audit_entries=audit_entries,
            limit=limit,
        ),
    )
