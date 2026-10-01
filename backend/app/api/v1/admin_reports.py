from datetime import date
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_report_support import _load_admin_reports, _load_admin_tasks, _serialize_task
from app.config import settings
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.reports.models import ReportTask
from app.models.user import User
from app.schemas.admin import (
    AdminReportListResponse,
    AdminReportResponse,
    AdminReportTaskListResponse,
    AdminReportTaskResponse,
)
from app.domains.audit.service import record_audit
from app.domains.reports.service import format_report_response, get_report_by_id
from app.domains.reports.task_service import create_report_task

router = APIRouter()


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
