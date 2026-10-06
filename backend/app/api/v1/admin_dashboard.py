from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import (
    CALENDAR_STATUS_LABELS,
    REPORT_STATUS_LABELS,
    USER_ROLE_LABELS,
    _count,
    _db_end,
    _db_start,
)
from app.api.v1.admin_activity_support import _load_audits
from app.api.v1.admin_dashboard_support import _daily_counts
from app.application.admin_service_sla import get_admin_report_request_sla
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.calendar.models import CalendarRequest, DecisionLog, UserCalendar
from app.domains.reports.models import Report, ReportTask
from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.service import (
    STALE_SERVICE_REQUEST_STATUSES,
    assignment_incomplete_condition,
)
from app.models.user import User
from app.domains.audit.models import AuditLog
from app.schemas.admin import (
    AuditLogResponse,
    DashboardAlert,
    DashboardDistributionItem,
    DashboardDistributionResponse,
    DashboardMetricResponse,
    DashboardOverviewResponse,
    DashboardTrendPoint,
)

router = APIRouter()
LOCAL_ZONE = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc


def _local_today() -> date:
    return datetime.now(LOCAL_ZONE).date()

def _dashboard_range(preset: str) -> tuple[date, date]:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(preset)
    if not days:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid dashboard range")
    end_date = _local_today()
    return end_date - timedelta(days=days - 1), end_date


async def _operation_alerts(db: AsyncSession, now: datetime | None = None) -> list[DashboardAlert]:
    current_time = now or datetime.utcnow()
    service_cutoff = current_time - timedelta(hours=24)
    calendar_cutoff = current_time - timedelta(minutes=45)
    open_report_request = (
        ServiceRequest.service_type == "report",
        ServiceRequest.status.not_in(("delivered", "withdrawn", "rejected")),
    )
    incomplete_assignment = assignment_incomplete_condition()

    counts = {
        "incomplete_assignment": await _count(
            db,
            select(func.count(ServiceRequest.id)).where(*open_report_request, incomplete_assignment),
        ),
        "incomplete_assignment_over_24h": await _count(
            db,
            select(func.count(ServiceRequest.id)).where(
                *open_report_request,
                incomplete_assignment,
                ServiceRequest.created_at < service_cutoff,
            ),
        ),
        "stale_service_requests": await _count(
            db,
            select(func.count(ServiceRequest.id)).where(
                ServiceRequest.service_type == "report",
                ServiceRequest.status.in_(STALE_SERVICE_REQUEST_STATUSES),
                ServiceRequest.updated_at < service_cutoff,
            ),
        ),
        "failed_service_requests": await _count(
            db,
            select(func.count(ServiceRequest.id)).where(
                ServiceRequest.service_type == "report",
                ServiceRequest.status == "failed",
            ),
        ),
        "failed_calendar_requests": await _count(
            db,
            select(func.count(CalendarRequest.id)).where(CalendarRequest.status == "failed"),
        ),
        "stalled_calendar_requests": await _count(
            db,
            select(func.count(CalendarRequest.id)).where(
                CalendarRequest.status == "generating",
                CalendarRequest.updated_at < calendar_cutoff,
            ),
        ),
    }
    definitions = (
        ("incomplete_assignment", "warning", "咨询师席位未完整分配", "requests"),
        ("incomplete_assignment_over_24h", "danger", "超过 24 小时未完成分配", "requests"),
        ("stale_service_requests", "warning", "工作流超过 24 小时未更新", "requests"),
        ("failed_service_requests", "danger", "服务申请处理失败", "requests"),
        ("failed_calendar_requests", "danger", "日历生成失败", "requests"),
        ("stalled_calendar_requests", "warning", "日历生成超过 45 分钟", "requests"),
    )
    return [
        DashboardAlert(key=key, level=level, label=label, count=counts[key], route=route)
        for key, level, label, route in definitions
        if counts[key]
    ]

async def _dashboard_data(db: AsyncSession, preset: str) -> DashboardOverviewResponse:
    start_date, end_date = _dashboard_range(preset)
    start_dt, end_dt = _db_start(start_date), _db_end(end_date)

    user_total = await _count(db, select(func.count(User.id)))
    active_users = await _count(db, select(func.count(User.id)).where(User.is_active.is_(True)))
    new_users = await _count(db, select(func.count(User.id)).where(User.created_at >= start_dt, User.created_at < end_dt))
    report_total = await _count(db, select(func.count(Report.id)).where(Report.is_deleted.is_(False)))
    report_processing = await _count(db, select(func.count(ReportTask.task_id)).where(ReportTask.status == "processing"))
    report_failed = await _count(db, select(func.count(ReportTask.task_id)).where(ReportTask.status == "failed"))
    task_finished = await _count(db, select(func.count(ReportTask.task_id)).where(
        ReportTask.created_at >= start_dt, ReportTask.created_at < end_dt, ReportTask.status.in_(["completed", "failed"])
    ))
    task_completed = await _count(db, select(func.count(ReportTask.task_id)).where(
        ReportTask.created_at >= start_dt, ReportTask.created_at < end_dt, ReportTask.status == "completed"
    ))
    success_rate = round(task_completed * 100 / task_finished, 1) if task_finished else 0
    published_calendars = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.status == "published"))
    decision_logs = await _count(db, select(func.count(DecisionLog.id)).where(DecisionLog.log_date >= start_date, DecisionLog.log_date <= end_date))

    role_rows = (await db.execute(select(User.role, func.count(User.id)).group_by(User.role))).all()
    report_rows = (await db.execute(select(Report.status, func.count(Report.id)).where(Report.is_deleted.is_(False)).group_by(Report.status))).all()
    calendar_rows = (await db.execute(select(UserCalendar.status, func.count(UserCalendar.id)).group_by(UserCalendar.status))).all()

    def distribution(rows, labels):
        return [DashboardDistributionItem(key=str(key or "unknown"), label=labels.get(key, "未分类"), value=int(value)) for key, value in rows]

    users_daily = await _daily_counts(db, User, User.id, User.created_at, start_date, end_date)
    reports_daily = await _daily_counts(db, Report, Report.id, Report.created_at, start_date, end_date)
    logs_daily = await _daily_counts(db, DecisionLog, DecisionLog.id, DecisionLog.log_date, start_date, end_date, use_log_date=True)
    trends = [
        DashboardTrendPoint(
            date=current,
            new_users=users_daily.get(current, 0),
            reports=reports_daily.get(current, 0),
            decision_logs=logs_daily.get(current, 0),
        )
        for offset in range((end_date - start_date).days + 1)
        for current in [start_date + timedelta(days=offset)]
    ]

    draft_calendars = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.status == "draft"))
    failed_logins = await _count(db, select(func.count(AuditLog.id)).where(
        AuditLog.action == "auth.login.failure", AuditLog.created_at >= start_dt, AuditLog.created_at < end_dt
    ))
    alerts = await _operation_alerts(db)
    if report_failed:
        alerts.append(DashboardAlert(key="failed_reports", level="danger", label="报告任务失败", count=report_failed, route="reports"))
    if draft_calendars:
        alerts.append(DashboardAlert(key="draft_calendars", level="info", label="待发布日历草稿", count=draft_calendars, route="calendar"))
    if failed_logins:
        alerts.append(DashboardAlert(key="failed_logins", level="danger", label="范围内失败登录", count=failed_logins, route="logs"))

    recent_activity, _ = await _load_audits(db, page=1, size=8)
    service_sla = await get_admin_report_request_sla(
        db,
        start_at=start_dt,
        end_at=end_dt,
    )
    return DashboardOverviewResponse(
        range_preset=preset,
        start_date=start_date,
        end_date=end_date,
        timezone="Asia/Shanghai",
        metrics=DashboardMetricResponse(
            user_total=user_total,
            active_users=active_users,
            new_users=new_users,
            report_total=report_total,
            report_success_rate=success_rate,
            report_processing=report_processing,
            report_failed=report_failed,
            published_calendars=published_calendars,
            decision_logs=decision_logs,
        ),
        trends=trends,
        distributions=DashboardDistributionResponse(
            users_by_role=distribution(role_rows, USER_ROLE_LABELS),
            reports_by_status=distribution(report_rows, REPORT_STATUS_LABELS),
            calendars_by_status=distribution(calendar_rows, CALENDAR_STATUS_LABELS),
        ),
        service_sla=service_sla,
        alerts=alerts,
        recent_activity=[AuditLogResponse.model_validate(item) for item in recent_activity],
    )

@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    range_preset: str = Query("30d", alias="range", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await _dashboard_data(db, range_preset)
