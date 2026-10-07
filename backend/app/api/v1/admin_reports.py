from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_report_support import _load_admin_reports, _load_admin_tasks
from app.api.v1.admin_support import _admin_access_details, _record_admin_data_access
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.admin import (
    AdminReportListResponse,
    AdminReportResponse,
    AdminReportTaskListResponse,
)
from app.domains.reports.service import format_report_response, get_report_by_id

router = APIRouter()


@router.get("/reports", response_model=AdminReportListResponse)
async def list_admin_reports(
    request: Request,
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
    await _record_admin_data_access(
        db,
        request,
        current_user,
        action="admin.reports.list",
        resource_type="report",
        target_user_id=user_id,
        details=_admin_access_details(
            page=page,
            page_size=size,
            result_count=len(items),
            filters={
                "status": report_status,
                "user_id": user_id,
                "search": search,
                "ai_model": ai_model,
                "date_from": date_from,
                "date_to": date_to,
            },
        ),
    )
    return AdminReportListResponse(total=total, page=page, size=size, items=items)

@router.get("/reports/{report_id}", response_model=AdminReportResponse)
async def get_admin_report(
    report_id: int,
    request: Request,
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
    payload.update({
        "user_id": user.id,
        "user_name": user.name,
        "user_phone": user.phone,
        "status": report.status,
        "is_deleted": report.is_deleted,
        "ai_model": report.ai_model,
        "generation_time_ms": report.generation_time_ms,
        "request_id": report.request_id,
        "birth_date": report.birth_date,
        "birth_time": report.birth_time,
        "birth_calendar_type": report.birth_calendar_type,
        "birth_place": report.birth_place,
        "selected_topics": report.selected_topics or [],
        "additional_info": report.additional_info,
    })
    await _record_admin_data_access(
        db,
        request,
        current_user,
        action="admin.report.read",
        resource_type="report",
        resource_id=str(report.id),
        target_user_id=user.id,
    )
    return payload

@router.get("/report-tasks", response_model=AdminReportTaskListResponse)
async def list_admin_report_tasks(
    request: Request,
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
    await _record_admin_data_access(
        db,
        request,
        current_user,
        action="admin.report_tasks.list",
        resource_type="report_task",
        target_user_id=user_id,
        details=_admin_access_details(
            page=page,
            page_size=size,
            result_count=len(items),
            filters={
                "status": task_status,
                "user_id": user_id,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        ),
    )
    return AdminReportTaskListResponse(total=total, page=page, size=size, items=items)

@router.post(
    "/report-tasks/{task_id}/retry",
    status_code=status.HTTP_410_GONE,
    deprecated=True,
)
async def retry_admin_report_task(
    task_id: str,
    current_user: User = Depends(require_roles("admin")),
):
    """Retired legacy retry; reports must be handled through a service request case."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="旧版报告任务不可重试，请在对应的服务申请工作流中继续处理。",
    )
