from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import (
    BOOKING_STATUS_LABELS,
    CALENDAR_STATUS_LABELS,
    REPORT_STATUS_LABELS,
    USER_ROLE_LABELS,
    _count,
    _daily_counts,
    _db_end,
    _db_start,
    _load_audits,
)
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.booking import Booking
from app.models.calendar import DecisionLog, UserCalendar
from app.models.course import Course, UserCourse
from app.models.report import Report, ReportTask
from app.models.user import AuditLog, User
from app.schemas.admin import (
    AuditLogResponse,
    DashboardAlert,
    DashboardCourseStat,
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
    booking_pending = await _count(db, select(func.count(Booking.id)).where(Booking.status == "pending"))
    booking_confirmed = await _count(db, select(func.count(Booking.id)).where(Booking.status == "confirmed"))
    booking_completed = await _count(db, select(func.count(Booking.id)).where(Booking.status == "completed"))
    published_calendars = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.status == "published"))
    decision_logs = await _count(db, select(func.count(DecisionLog.id)).where(DecisionLog.log_date >= start_date, DecisionLog.log_date <= end_date))
    active_learners = await _count(db, select(func.count(func.distinct(UserCourse.user_id))).where(UserCourse.status == "active"))
    course_rows = (await db.execute(
        select(
            Course.id,
            Course.title,
            Course.total_lessons,
            func.count(UserCourse.id),
            func.count(UserCourse.id).filter(UserCourse.status == "active"),
            func.count(UserCourse.id).filter(UserCourse.status == "completed"),
            func.avg(UserCourse.progress_percentage),
        )
        .outerjoin(UserCourse, UserCourse.course_id == Course.id)
        .group_by(Course.id, Course.title, Course.total_lessons)
        .order_by(func.count(UserCourse.id).desc(), Course.id)
    )).all()

    role_rows = (await db.execute(select(User.role, func.count(User.id)).group_by(User.role))).all()
    booking_rows = (await db.execute(select(Booking.status, func.count(Booking.id)).group_by(Booking.status))).all()
    report_rows = (await db.execute(select(Report.status, func.count(Report.id)).where(Report.is_deleted.is_(False)).group_by(Report.status))).all()
    calendar_rows = (await db.execute(select(UserCalendar.status, func.count(UserCalendar.id)).group_by(UserCalendar.status))).all()

    def distribution(rows, labels):
        return [DashboardDistributionItem(key=str(key or "unknown"), label=labels.get(key, "未分类"), value=int(value)) for key, value in rows]

    users_daily = await _daily_counts(db, User, User.id, User.created_at, start_date, end_date)
    reports_daily = await _daily_counts(db, Report, Report.id, Report.created_at, start_date, end_date)
    bookings_daily = await _daily_counts(db, Booking, Booking.id, Booking.created_at, start_date, end_date)
    logs_daily = await _daily_counts(db, DecisionLog, DecisionLog.id, DecisionLog.log_date, start_date, end_date, use_log_date=True)
    trends = [
        DashboardTrendPoint(
            date=current,
            new_users=users_daily.get(current, 0),
            reports=reports_daily.get(current, 0),
            bookings=bookings_daily.get(current, 0),
            decision_logs=logs_daily.get(current, 0),
        )
        for offset in range((end_date - start_date).days + 1)
        for current in [start_date + timedelta(days=offset)]
    ]

    draft_calendars = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.status == "draft"))
    failed_logins = await _count(db, select(func.count(AuditLog.id)).where(
        AuditLog.action == "auth.login.failure", AuditLog.created_at >= start_dt, AuditLog.created_at < end_dt
    ))
    alerts = []
    if booking_pending:
        alerts.append(DashboardAlert(key="pending_bookings", level="warning", label="待确认预约", count=booking_pending, route="bookings"))
    if report_failed:
        alerts.append(DashboardAlert(key="failed_reports", level="danger", label="报告任务失败", count=report_failed, route="reports"))
    if draft_calendars:
        alerts.append(DashboardAlert(key="draft_calendars", level="info", label="待发布日历草稿", count=draft_calendars, route="calendar"))
    if failed_logins:
        alerts.append(DashboardAlert(key="failed_logins", level="danger", label="范围内失败登录", count=failed_logins, route="logs"))

    recent_activity, _ = await _load_audits(db, page=1, size=8)
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
            booking_pending=booking_pending,
            booking_confirmed=booking_confirmed,
            booking_completed=booking_completed,
            published_calendars=published_calendars,
            decision_logs=decision_logs,
            active_learners=active_learners,
        ),
        trends=trends,
        distributions=DashboardDistributionResponse(
            users_by_role=distribution(role_rows, USER_ROLE_LABELS),
            bookings_by_status=distribution(booking_rows, BOOKING_STATUS_LABELS),
            reports_by_status=distribution(report_rows, REPORT_STATUS_LABELS),
            calendars_by_status=distribution(calendar_rows, CALENDAR_STATUS_LABELS),
        ),
        course_stats=[
            DashboardCourseStat(
                course_id=course_id,
                title=title,
                total_lessons=int(total_lessons or 0),
                enrolled_count=int(enrolled_count or 0),
                active_count=int(active_count or 0),
                completed_count=int(completed_count or 0),
                completion_rate=round((int(completed_count or 0) * 100 / int(enrolled_count)) if enrolled_count else 0, 1),
                average_progress=round(float(average_progress or 0), 1),
            )
            for course_id, title, total_lessons, enrolled_count, active_count, completed_count, average_progress in course_rows
        ],
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
