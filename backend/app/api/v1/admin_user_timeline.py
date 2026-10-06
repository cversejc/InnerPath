from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.audit.models import AuditLog
from app.domains.calendar.models import CalendarRequest, DecisionLog, UserCalendar
from app.domains.reports.models import Report, ReportTask
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.models import ReportCase, StepTask
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
    report_cases = await recent(ReportCase, ReportCase.user_id == user_id)
    workflow_instance_ids = [
        item.workflow_instance_id
        for item in report_cases
        if item.workflow_instance_id is not None
    ]
    workflow_steps = []
    workflow_audit_entries = []
    if workflow_instance_ids:
        workflow_steps = list(
            (
                await db.scalars(
                    select(StepTask)
                    .where(StepTask.workflow_instance_id.in_(workflow_instance_ids))
                    .order_by(StepTask.updated_at.desc())
                    .limit(1000)
                )
            ).all()
        )
        case_ids = [str(item.id) for item in report_cases]
        workflow_audit_entries = list(
            (
                await db.execute(
                    select(AuditLog, User.name)
                    .outerjoin(User, AuditLog.actor_user_id == User.id)
                    .where(
                        AuditLog.resource_type == "report_case",
                        AuditLog.resource_id.in_(case_ids),
                        AuditLog.action.in_(
                            (
                                "workflow.step.assign",
                                "workflow.step.return",
                                "workflow.step.reopen",
                                "report_case.info_requested",
                                "report_case.info_answered",
                                "report_case.deliver",
                            )
                        ),
                        AuditLog.target_user_id.is_(None),
                    )
                    .order_by(AuditLog.created_at.desc())
                    .limit(500)
                )
            ).all()
        )
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
            report_cases=report_cases,
            workflow_steps=workflow_steps,
            workflow_audit_entries=workflow_audit_entries,
            limit=limit,
        ),
    )
