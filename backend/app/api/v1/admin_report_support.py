from datetime import date
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import _count, _date_filter
from app.domains.reports.models import Report, ReportTask
from app.models.user import User


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
