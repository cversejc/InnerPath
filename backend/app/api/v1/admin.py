import csv
import io
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.config import settings
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.booking import Booking
from app.models.calendar import DecisionLog, UserCalendar
from app.models.course import Course, UserCourse
from app.models.report import Report, ReportTask
from app.models.user import AuditLog, User
from app.schemas.admin import (
    AdminBookingListResponse,
    AdminBookingResponse,
    AdminDecisionLogListResponse,
    AdminPasswordResetRequest,
    AdminReportListResponse,
    AdminReportResponse,
    AdminReportTaskListResponse,
    AdminReportTaskResponse,
    AdminUserListResponse,
    AdminUserSummaryResponse,
    AdminUserUpdate,
    AuditLogListResponse,
    AuditLogResponse,
    DashboardAlert,
    DashboardCourseStat,
    DashboardDistributionItem,
    DashboardDistributionResponse,
    DashboardMetricResponse,
    DashboardOverviewResponse,
    DashboardTrendPoint,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.schemas.booking import BookingAdminUpdate, BookingResponse
from app.schemas.calendar import (
    CalendarCreate,
    CalendarImportRequest,
    CalendarListResponse,
    CalendarResponse,
    CalendarUpdate,
    StaffInviteCreate,
    StaffInviteResponse,
)
from app.schemas.course import UserCourseProgressUpdate
from app.schemas.user import UserResponse
from app.services.audit_service import parse_audit_details, record_audit
from app.services.auth_service import admin_reset_password, create_staff_invite
from app.services.booking_service import update_booking
from app.services.calendar_service import (
    archive_calendar,
    clone_calendar_as_draft,
    create_calendar,
    get_user_calendars,
    publish_calendar,
    serialize_calendar,
    update_calendar,
)
from app.services.report_service import create_report_task, format_report_response, get_report_by_id


router = APIRouter()
LOCAL_ZONE = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc

USER_ROLE_LABELS = {"user": "用户", "consultant": "咨询师", "admin": "管理员"}
BOOKING_STATUS_LABELS = {
    "pending": "待确认",
    "confirmed": "已确认",
    "completed": "已完成",
    "cancelled": "已取消",
}
REPORT_STATUS_LABELS = {"processing": "生成中", "completed": "已完成", "failed": "失败"}
CALENDAR_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}


def _local_today() -> date:
    return datetime.now(LOCAL_ZONE).date()


def _db_start(date_value: date) -> datetime:
    return datetime.combine(date_value, time.min, tzinfo=LOCAL_ZONE).astimezone(UTC).replace(tzinfo=None)


def _db_end(date_value: date) -> datetime:
    return datetime.combine(date_value + timedelta(days=1), time.min, tzinfo=LOCAL_ZONE).astimezone(UTC).replace(tzinfo=None)


def _dashboard_range(preset: str) -> tuple[date, date]:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(preset)
    if not days:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid dashboard range")
    end_date = _local_today()
    return end_date - timedelta(days=days - 1), end_date


async def _count(db: AsyncSession, statement) -> int:
    return int((await db.scalar(statement)) or 0)


async def _float_value(db: AsyncSession, statement) -> float:
    return float((await db.scalar(statement)) or 0)


def _date_filter(column, date_from: Optional[date], date_to: Optional[date]):
    conditions = []
    if date_from:
        conditions.append(column >= _db_start(date_from))
    if date_to:
        conditions.append(column < _db_end(date_to))
    return conditions


def _serialize_audit(log: AuditLog, actor_name: Optional[str] = None, target_name: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details,
        "details_json": parse_audit_details(log.details),
        "ip_address": log.ip_address,
        "target_user_id": log.target_user_id,
        "actor_name": actor_name,
        "target_user_name": target_name,
        "request_id": log.request_id,
        "user_agent": log.user_agent,
        "created_at": log.created_at,
    }


def _serialize_admin_booking(booking: Booking, user: Optional[User] = None) -> dict[str, Any]:
    payload = {field: getattr(booking, field) for field in (
        "id", "user_id", "service_name", "service_type", "service_price", "preferred_time",
        "confirmed_date", "confirmed_time", "consultant_name", "consultant_id", "contact_phone",
        "topics", "notes", "meeting_url", "meeting_notes", "cancellation_reason", "status", "created_at", "updated_at",
    )}
    payload["user_name"] = user.name if user else None
    payload["user_phone"] = user.phone if user else None
    return payload


def _serialize_report(report: Report, user: User, task: Optional[ReportTask] = None) -> dict[str, Any]:
    energy_profile = report.energy_profile or {}
    return {
        "id": report.id,
        "title": report.title,
        "created_at": report.created_at,
        "energy_type": energy_profile.get("type"),
        "core_traits": energy_profile.get("core_traits") or energy_profile.get("coreTraits"),
        "user_id": user.id,
        "user_name": user.name,
        "user_phone": user.phone,
        "status": report.status,
        "is_deleted": report.is_deleted,
        "ai_model": report.ai_model,
        "generation_time_ms": report.generation_time_ms,
        "task_id": task.task_id if task else None,
        "task_status": task.status if task else None,
        "task_progress": task.progress if task else None,
        "task_error": task.error if task else None,
    }


def _serialize_task(task: ReportTask, user: Optional[User] = None, has_retry: bool = False) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "user_id": task.user_id,
        "user_name": user.name if user else None,
        "status": task.status,
        "progress": task.progress,
        "report_id": task.report_id,
        "error": task.error,
        "retry_count": task.retry_count,
        "retry_of_task_id": task.retry_of_task_id,
        "has_input_snapshot": bool(task.input_snapshot),
        "has_retry": has_retry,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


async def _load_audits(
    db: AsyncSession,
    *,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    actor = aliased(User)
    target = aliased(User)
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if actor_user_id is not None:
        conditions.append(AuditLog.actor_user_id == actor_user_id)
    if target_user_id is not None:
        conditions.append(AuditLog.target_user_id == target_user_id)
    conditions.extend(_date_filter(AuditLog.created_at, date_from, date_to))
    if search:
        like = f"%{search}%"
        conditions.append(or_(AuditLog.action.ilike(like), AuditLog.resource_type.ilike(like), AuditLog.resource_id.ilike(like), AuditLog.details.ilike(like), actor.name.ilike(like), target.name.ilike(like)))

    count_statement = (
        select(func.count(AuditLog.id))
        .select_from(AuditLog)
        .outerjoin(actor, AuditLog.actor_user_id == actor.id)
        .outerjoin(target, AuditLog.target_user_id == target.id)
    )
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)

    statement = (
        select(AuditLog, actor.name, target.name)
        .outerjoin(actor, AuditLog.actor_user_id == actor.id)
        .outerjoin(target, AuditLog.target_user_id == target.id)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    return [_serialize_audit(log, actor_name, target_name) for log, actor_name, target_name in rows], total


async def _load_admin_bookings(
    db: AsyncSession,
    *,
    booking_status: Optional[str] = None,
    consultant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    conditions = []
    if booking_status:
        conditions.append(Booking.status == booking_status)
    if consultant_id is not None:
        conditions.append(Booking.consultant_id == consultant_id)
    if user_id is not None:
        conditions.append(Booking.user_id == user_id)
    conditions.extend(_date_filter(Booking.created_at, date_from, date_to))
    if search:
        like = f"%{search}%"
        conditions.append(or_(User.name.ilike(like), User.phone.ilike(like), Booking.service_name.ilike(like)))

    count_statement = select(func.count(Booking.id)).select_from(Booking).join(User, Booking.user_id == User.id)
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)

    statement = (
        select(Booking, User)
        .join(User, Booking.user_id == User.id)
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    return [_serialize_admin_booking(booking, user) for booking, user in rows], total


async def _load_admin_reports(
    db: AsyncSession,
    *,
    report_status: Optional[str] = None,
    ai_model: Optional[str] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    conditions = [Report.is_deleted.is_(False)]
    if report_status:
        conditions.append(Report.status == report_status)
    if ai_model:
        conditions.append(Report.ai_model == ai_model)
    if user_id is not None:
        conditions.append(Report.user_id == user_id)
    conditions.extend(_date_filter(Report.created_at, date_from, date_to))
    if search:
        like = f"%{search}%"
        conditions.append(or_(User.name.ilike(like), User.phone.ilike(like), Report.title.ilike(like)))

    count_statement = select(func.count(Report.id)).select_from(Report).join(User, Report.user_id == User.id).where(*conditions)
    total = await _count(db, count_statement)
    statement = (
        select(Report, User)
        .join(User, Report.user_id == User.id)
        .where(*conditions)
        .order_by(Report.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(statement)).all()
    reports = [report for report, _ in rows]
    task_map: dict[int, ReportTask] = {}
    if reports:
        task_rows = (await db.execute(
            select(ReportTask)
            .where(ReportTask.report_id.in_([report.id for report in reports]))
            .order_by(ReportTask.updated_at.desc())
        )).scalars().all()
        for task in task_rows:
            task_map.setdefault(task.report_id, task)
    return [_serialize_report(report, user, task_map.get(report.id)) for report, user in rows], total


async def _load_admin_tasks(
    db: AsyncSession,
    *,
    task_status: Optional[str] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    conditions = []
    if task_status:
        conditions.append(ReportTask.status == task_status)
    if user_id is not None:
        conditions.append(ReportTask.user_id == user_id)
    conditions.extend(_date_filter(ReportTask.created_at, date_from, date_to))
    if search:
        like = f"%{search}%"
        conditions.append(or_(User.name.ilike(like), User.phone.ilike(like), ReportTask.task_id.ilike(like)))
    count_statement = select(func.count(ReportTask.task_id)).select_from(ReportTask).join(User, ReportTask.user_id == User.id)
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)
    statement = (
        select(ReportTask, User)
        .join(User, ReportTask.user_id == User.id)
        .order_by(ReportTask.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    task_ids = [task.task_id for task, _ in rows]
    retry_ids = set()
    if task_ids:
        retry_ids = set((await db.execute(
            select(ReportTask.retry_of_task_id).where(ReportTask.retry_of_task_id.in_(task_ids))
        )).scalars().all())
    return [_serialize_task(task, user, task.task_id in retry_ids) for task, user in rows], total


async def _load_decision_logs(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    kind: Optional[str] = None,
    log_status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    conditions = []
    if user_id is not None:
        conditions.append(DecisionLog.user_id == user_id)
    if kind:
        conditions.append(DecisionLog.kind == kind)
    if log_status:
        conditions.append(DecisionLog.status == log_status)
    if date_from:
        conditions.append(DecisionLog.log_date >= date_from)
    if date_to:
        conditions.append(DecisionLog.log_date <= date_to)
    if search:
        like = f"%{search}%"
        conditions.append(or_(User.name.ilike(like), User.phone.ilike(like), DecisionLog.content.ilike(like)))

    count_statement = select(func.count(DecisionLog.id)).select_from(DecisionLog).join(User, DecisionLog.user_id == User.id)
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)
    statement = (
        select(DecisionLog, User)
        .join(User, DecisionLog.user_id == User.id)
        .order_by(DecisionLog.log_date.desc(), DecisionLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user.name,
            "log_date": log.log_date,
            "kind": log.kind,
            "status": log.status,
            "content": log.content,
            "note": log.note,
            "created_at": log.created_at,
            "updated_at": log.updated_at,
        }
        for log, user in rows
    ], total


async def _daily_counts(
    db: AsyncSession,
    model,
    id_column,
    timestamp_column,
    start_date: date,
    end_date: date,
    *,
    use_log_date: bool = False,
) -> dict[date, int]:
    if use_log_date:
        day_expression = timestamp_column
        conditions = [timestamp_column >= start_date, timestamp_column <= end_date]
    else:
        day_expression = func.date(timestamp_column + text("interval '8 hours'"))
        conditions = [timestamp_column >= _db_start(start_date), timestamp_column < _db_end(end_date)]
    statement = (
        select(day_expression.label("day"), func.count(id_column))
        .select_from(model)
        .where(*conditions)
        .group_by(day_expression)
    )
    rows = (await db.execute(statement)).all()
    return {row[0]: int(row[1]) for row in rows}


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


async def _get_calendar_or_404(db: AsyncSession, calendar_id: int) -> UserCalendar:
    calendar = await db.get(UserCalendar, calendar_id)
    if not calendar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return calendar


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    range_preset: str = Query("30d", alias="range", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await _dashboard_data(db, range_preset)


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, pattern="^(user|consultant|admin)$"),
    is_active: Optional[bool] = None,
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if search:
        conditions.append(or_(User.name.ilike(f"%{search}%"), User.phone.ilike(f"%{search}%")))
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    conditions.extend(_date_filter(User.created_at, created_from, created_to))

    report_count = select(func.count(Report.id)).where(Report.user_id == User.id, Report.is_deleted.is_(False)).correlate(User).scalar_subquery()
    booking_count = select(func.count(Booking.id)).where(Booking.user_id == User.id).correlate(User).scalar_subquery()
    calendar_count = select(func.count(UserCalendar.id)).where(UserCalendar.user_id == User.id).correlate(User).scalar_subquery()
    count_statement = select(func.count(User.id))
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)
    statement = (
        select(User, report_count.label("report_count"), booking_count.label("booking_count"), calendar_count.label("calendar_count"))
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    items = [
        {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "user_type": user.user_type,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "report_count": int(report_count_value or 0),
            "booking_count": int(booking_count_value or 0),
            "calendar_count": int(calendar_count_value or 0),
        }
        for user, report_count_value, booking_count_value, calendar_count_value in rows
    ]
    return AdminUserListResponse(total=total, page=page, size=size, items=items)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_profile_by_admin(
    user_id: int,
    data: AdminUserUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if "name" in data.model_fields_set and data.name is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty")
    changed_fields = []
    for field, value in data.model_dump(exclude_unset=True).items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed_fields.append(field)
    if changed_fields:
        await record_audit(
            db,
            current_user.id,
            "user.profile.update.admin",
            "user",
            str(user.id),
            target_user_id=user.id,
            details={"changed_fields": changed_fields},
            request=request,
        )
        await db.commit()
        await db.refresh(user)
    return user


@router.get("/users/{user_id}/summary", response_model=AdminUserSummaryResponse)
async def get_user_summary(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    report_count = await _count(db, select(func.count(Report.id)).where(Report.user_id == user_id, Report.is_deleted.is_(False)))
    booking_count = await _count(db, select(func.count(Booking.id)).where(Booking.user_id == user_id))
    calendar_count = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.user_id == user_id))
    published_calendar_count = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.user_id == user_id, UserCalendar.status == "published"))
    decision_log_count = await _count(db, select(func.count(DecisionLog.id)).where(DecisionLog.user_id == user_id))
    course_count = await _count(db, select(func.count(UserCourse.id)).where(UserCourse.user_id == user_id))
    average_progress = await _float_value(db, select(func.avg(UserCourse.progress_percentage)).where(UserCourse.user_id == user_id))
    return {
        "user": user,
        "summary": {
            "report_count": report_count,
            "booking_count": booking_count,
            "calendar_count": calendar_count,
            "published_calendar_count": published_calendar_count,
            "decision_log_count": decision_log_count,
            "course_count": course_count,
            "average_course_progress": round(average_progress, 1),
        },
    }


@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    request_data: UserStatusUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.id == user.id and not request_data.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
    if user.role == "admin" and user.is_active and not request_data.is_active:
        active_admins = await _count(db, select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True)))
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the last admin")
    old_status = user.is_active
    user.is_active = request_data.is_active
    await record_audit(
        db,
        current_user.id,
        "user.status.update",
        "user",
        str(user.id),
        target_user_id=user.id,
        details={"old_is_active": old_status, "is_active": user.is_active},
        request=request,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    request_data: UserRoleUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == "admin" and request_data.role != "admin" and user.is_active:
        active_admins = await _count(db, select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True)))
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the last admin")
    old_role = user.role
    user.role = request_data.role
    await record_audit(
        db,
        current_user.id,
        "user.role.update",
        "user",
        str(user.id),
        target_user_id=user.id,
        details={"old_role": old_role, "new_role": user.role},
        request=request,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/password/reset")
async def reset_user_password_by_admin(
    user_id: int,
    request_data: AdminPasswordResetRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await admin_reset_password(db, user, request_data.new_password)
    await record_audit(db, current_user.id, "user.password.reset", "user", str(user.id), target_user_id=user.id, request=request)
    await db.commit()
    return {"success": True, "message": "Password reset successfully"}


@router.post("/staff/invites", response_model=StaffInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    data: StaffInviteCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    invite, token = await create_staff_invite(db, data.phone, data.role, current_user.id)
    await record_audit(db, current_user.id, "staff.invite.create", "staff_invite", str(invite.id), details={"role": data.role}, request=request)
    await db.commit()
    return StaffInviteResponse(id=invite.id, phone=invite.phone, role=invite.role, token=token, expires_at=invite.expires_at)


@router.get("/users/{user_id}/calendars", response_model=CalendarListResponse)
async def list_user_calendars(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return CalendarListResponse(items=await get_user_calendars(db, user_id, published_only=False))


@router.post("/users/{user_id}/calendars", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_user_calendar(
    user_id: int,
    data: CalendarCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        calendar = await create_calendar(db, user_id, current_user.id, data, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)


@router.post("/calendars/import", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def import_calendar(
    data: CalendarImportRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, data.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        calendar = await create_calendar(
            db,
            data.user_id,
            current_user.id,
            CalendarCreate(title=data.title, start_date=data.start_date, end_date=data.end_date, entries=data.entries),
            request=request,
        )
        await record_audit(
            db,
            current_user.id,
            "calendar.import",
            "calendar",
            str(calendar.id),
            target_user_id=data.user_id,
            details={"entry_count": len(data.entries)},
            request=request,
        )
        await db.commit()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)


@router.post("/calendars/{calendar_id}/draft", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_draft(
    calendar_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    draft = await clone_calendar_as_draft(db, calendar, current_user.id, request=request)
    return await serialize_calendar(db, draft)


@router.put("/calendars/{calendar_id}", response_model=CalendarResponse)
async def update_user_calendar(
    calendar_id: int,
    data: CalendarUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    try:
        calendar = await update_calendar(db, calendar, current_user.id, data, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)


@router.post("/calendars/{calendar_id}/publish", response_model=CalendarResponse)
async def publish_user_calendar(
    calendar_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    try:
        calendar = await publish_calendar(db, calendar, current_user.id, request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return await serialize_calendar(db, calendar)


@router.post("/calendars/{calendar_id}/archive", response_model=CalendarResponse)
async def archive_user_calendar(
    calendar_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await _get_calendar_or_404(db, calendar_id)
    calendar = await archive_calendar(db, calendar, current_user.id, request=request)
    return await serialize_calendar(db, calendar)


@router.get("/bookings", response_model=AdminBookingListResponse)
async def list_admin_bookings(
    booking_status: Optional[str] = Query(None, alias="status", pattern="^(pending|confirmed|completed|cancelled)$"),
    consultant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_admin_bookings(db, booking_status=booking_status, consultant_id=consultant_id, user_id=user_id, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminBookingListResponse(total=total, page=page, size=size, items=items)


@router.patch("/bookings/{booking_id}", response_model=AdminBookingResponse)
async def update_admin_booking(
    booking_id: int,
    data: BookingAdminUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    before = {field: getattr(booking, field) for field in data.model_dump(exclude_unset=True)}
    try:
        booking = await update_booking(db, booking_id, data, commit=False)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    await record_audit(
        db,
        current_user.id,
        "booking.update",
        "booking",
        str(booking.id),
        target_user_id=booking.user_id,
        details={"before": {key: str(value) for key, value in before.items()}, "changed_fields": list(before.keys())},
        request=request,
    )
    await db.commit()
    await db.refresh(booking)
    user = await db.get(User, booking.user_id)
    return _serialize_admin_booking(booking, user)


@router.get("/users/{user_id}/bookings", response_model=AdminBookingListResponse)
async def list_user_bookings(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    items, total = await _load_admin_bookings(db, user_id=user_id, page=page, size=size)
    return AdminBookingListResponse(total=total, page=page, size=size, items=items)


@router.get("/decision-logs", response_model=AdminDecisionLogListResponse)
async def list_admin_decision_logs(
    user_id: Optional[int] = None,
    kind: Optional[str] = Query(None, pattern="^(action|decision)$"),
    log_status: Optional[str] = Query(None, alias="status", pattern="^(done|doing|skipped)$"),
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_decision_logs(db, user_id=user_id, kind=kind, log_status=log_status, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminDecisionLogListResponse(total=total, page=page, size=size, items=items)


@router.get("/users/{user_id}/decision-logs", response_model=AdminDecisionLogListResponse)
async def list_user_decision_logs(
    user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    items, total = await _load_decision_logs(db, user_id=user_id, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminDecisionLogListResponse(total=total, page=page, size=size, items=items)


@router.get("/reports", response_model=AdminReportListResponse)
async def list_admin_reports(
    report_status: Optional[str] = Query(None, alias="status", pattern="^(processing|completed|failed)$"),
    user_id: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    ai_model: Optional[str] = Query(None, max_length=50),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_admin_reports(db, report_status=report_status, user_id=user_id, search=search, ai_model=ai_model, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminReportListResponse(total=total, page=page, size=size, items=items)


@router.get("/reports/{report_id}", response_model=AdminReportResponse)
async def get_admin_report(
    report_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    report = await get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    user = await db.get(User, report.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    payload = format_report_response(report)
    payload.update({"user_id": user.id, "user_name": user.name, "user_phone": user.phone, "status": report.status, "is_deleted": report.is_deleted, "ai_model": report.ai_model, "generation_time_ms": report.generation_time_ms})
    return payload


@router.get("/report-tasks", response_model=AdminReportTaskListResponse)
async def list_admin_report_tasks(
    task_status: Optional[str] = Query(None, alias="status", pattern="^(processing|completed|failed)$"),
    user_id: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_admin_tasks(db, task_status=task_status, user_id=user_id, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminReportTaskListResponse(total=total, page=page, size=size, items=items)


@router.post("/report-tasks/{task_id}/retry", response_model=AdminReportTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_admin_report_task(
    task_id: str,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    task = (await db.execute(
        select(ReportTask).where(ReportTask.task_id == task_id).with_for_update()
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed tasks can be retried")
    if not task.input_snapshot:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task input is unavailable")
    existing_retry = await db.scalar(
        select(ReportTask.task_id).where(ReportTask.retry_of_task_id == task.task_id).limit(1)
    )
    if existing_retry:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already has a retry")
    if task.retry_count >= settings.REPORT_MAX_RETRIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Retry limit reached")

    new_task_id = str(uuid4())
    new_task = await create_report_task(db, new_task_id, task.user_id, input_snapshot=task.input_snapshot, retry_count=task.retry_count + 1, retry_of_task_id=task.task_id)
    from app.tasks.report_tasks import generate_report_task

    try:
        generate_report_task.apply_async(args=[task.user_id, task.input_snapshot], task_id=new_task_id)
    except Exception as error:
        new_task.status = "failed"
        new_task.error = str(error)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to queue retry")
    await record_audit(
        db,
        current_user.id,
        "report.task.retry",
        "report_task",
        new_task_id,
        target_user_id=task.user_id,
        details={"retry_of_task_id": task.task_id, "retry_count": new_task.retry_count},
        request=request,
    )
    await db.commit()
    await db.refresh(new_task)
    user = await db.get(User, task.user_id)
    return _serialize_task(new_task, user)


@router.get("/courses/users/{user_id}")
async def list_user_courses(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.course_service import get_user_courses

    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"items": await get_user_courses(db, user_id)}


@router.patch("/courses/users/{user_id}/{course_id}/progress")
async def update_user_course_progress_for_admin(
    user_id: int,
    course_id: int,
    data: UserCourseProgressUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.course_service import update_course_progress_for_admin

    try:
        user_course = await update_course_progress_for_admin(db, user_id, course_id, data)
    except ValueError as error:
        if str(error) == "completed_lessons_exceed_total":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Completed lessons exceed course total")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await record_audit(
        db,
        current_user.id,
        "course.progress.update",
        "user_course",
        str(user_course.id),
        target_user_id=user_id,
        details={"progress_percentage": data.progress_percentage, "completed_lessons": data.completed_lessons},
        request=request,
    )
    await db.commit()
    return {"course_id": user_course.course_id, "user_id": user_course.user_id, "progress": user_course.progress_percentage, "completed_lessons": user_course.completed_lessons, "status": user_course.status}


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(None, max_length=100),
    resource_type: Optional[str] = Query(None, max_length=50),
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_audits(db, action=action, resource_type=resource_type, actor_user_id=actor_user_id, target_user_id=target_user_id, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AuditLogListResponse(total=total, page=page, size=size, items=[AuditLogResponse.model_validate(item) for item in items])


def _csv_response(filename: str, headers: list[str], rows: list[list[Any]]) -> Response:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(content=buffer.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/exports/{resource}.csv")
async def export_admin_resource(
    resource: str,
    request: Request,
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, pattern="^(user|consultant|admin)$"),
    is_active: Optional[bool] = None,
    record_status: Optional[str] = Query(None, alias="status"),
    consultant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = Query(None, max_length=100),
    resource_type: Optional[str] = Query(None, max_length=50),
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    ai_model: Optional[str] = Query(None, max_length=50),
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    limit = settings.ADMIN_EXPORT_MAX_ROWS
    if resource == "users":
        conditions = []
        if search:
            conditions.append(or_(User.name.ilike(f"%{search}%"), User.phone.ilike(f"%{search}%")))
        if role:
            conditions.append(User.role == role)
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        conditions.extend(_date_filter(User.created_at, created_from or date_from, created_to or date_to))
        statement = select(User).order_by(User.created_at.desc()).limit(limit)
        if conditions:
            statement = statement.where(*conditions)
        users = (await db.execute(statement)).scalars().all()
        rows = [[user.id, user.name, user.phone, USER_ROLE_LABELS.get(user.role, user.role), "正常" if user.is_active else "已停用", user.created_at, user.last_login_at] for user in users]
        return _csv_response("users.csv", ["ID", "姓名", "手机号", "角色", "状态", "注册时间", "最近登录"], rows)
    if resource == "bookings":
        items, _ = await _load_admin_bookings(db, booking_status=record_status, consultant_id=consultant_id, user_id=user_id, search=search, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["user_name"], item["user_phone"], item["service_name"], BOOKING_STATUS_LABELS.get(item["status"], item["status"]), item["consultant_name"], item["confirmed_date"], item["confirmed_time"], item["created_at"]] for item in items]
        return _csv_response("bookings.csv", ["ID", "用户", "联系方式", "服务", "状态", "咨询师", "确认日期", "确认时间", "创建时间"], rows)
    if resource == "reports":
        items, _ = await _load_admin_reports(db, report_status=record_status, user_id=user_id, search=search, ai_model=ai_model, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["user_name"], item["user_phone"], item["title"], REPORT_STATUS_LABELS.get(item["status"], item["status"]), item["ai_model"], item["generation_time_ms"], item["created_at"]] for item in items]
        return _csv_response("reports.csv", ["ID", "用户", "联系方式", "标题", "状态", "模型", "生成耗时(ms)", "创建时间"], rows)
    if resource == "decision-logs":
        items, _ = await _load_decision_logs(db, user_id=user_id, log_status=record_status, search=search, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["user_id"], item["user_name"], item["log_date"], item["kind"], item["status"], item["content"], item["note"], item["created_at"]] for item in items]
        return _csv_response("decision-logs.csv", ["ID", "用户ID", "用户", "记录日期", "类型", "状态", "内容", "备注", "创建时间"], rows)
    if resource == "audit-logs":
        items, _ = await _load_audits(db, action=action, resource_type=resource_type, actor_user_id=actor_user_id, target_user_id=target_user_id, search=search, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["created_at"], item["action"], item["resource_type"], item["resource_id"], item["actor_name"] or item["actor_user_id"], item["target_user_name"] or item["target_user_id"], item["ip_address"], item["request_id"], item["details"]] for item in items]
        return _csv_response("audit-logs.csv", ["ID", "时间", "操作", "资源类型", "资源ID", "操作者", "目标用户", "IP", "请求ID", "详情"], rows)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported export resource")
