"""Shared query and serialization helpers for admin resource routes."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.booking import Booking
from app.models.calendar import DecisionLog, UserCalendar
from app.models.report import Report, ReportTask
from app.models.user import AuditLog, User
from app.services.audit_service import parse_audit_details


USER_ROLE_LABELS = {"user": "用户", "consultant": "咨询师", "admin": "管理员"}
BOOKING_STATUS_LABELS = {
    "pending": "待确认",
    "confirmed": "已确认",
    "completed": "已完成",
    "cancelled": "已取消",
}
REPORT_STATUS_LABELS = {"processing": "生成中", "completed": "已完成", "failed": "失败"}
CALENDAR_STATUS_LABELS = {"draft": "草稿", "published": "已发布", "archived": "已归档"}
LOCAL_ZONE = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc

def _db_start(date_value: date) -> datetime:
    return datetime.combine(date_value, time.min, tzinfo=LOCAL_ZONE).astimezone(UTC).replace(tzinfo=None)

def _db_end(date_value: date) -> datetime:
    return datetime.combine(date_value + timedelta(days=1), time.min, tzinfo=LOCAL_ZONE).astimezone(UTC).replace(tzinfo=None)

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

async def _get_calendar_or_404(db: AsyncSession, calendar_id: int) -> UserCalendar:
    calendar = await db.get(UserCalendar, calendar_id)
    if not calendar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return calendar
