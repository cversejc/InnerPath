import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.booking import Booking
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportListItem,
    ReportListResponse,
    ReportResponse,
    ReportTaskResponse,
    ReportTaskStatusResponse,
)
from app.services.report_service import (
    create_report_task,
    delete_report,
    format_report_response,
    get_report_task,
    get_report_task_by_id,
    get_report_by_id,
    get_user_reports,
)
from app.tasks.report_tasks import generate_report_task

router = APIRouter()
logger = get_logger(__name__)


def format_report_list(reports):
    items = []
    for report in reports:
        energy_profile = report.energy_profile or {}
        items.append(
            ReportListItem(
                id=report.id,
                title=report.title,
                created_at=report.created_at,
                energy_type=energy_profile.get("type"),
                core_traits=energy_profile.get("core_traits") or energy_profile.get("coreTraits"),
            )
        )
    return items


@router.post("", response_model=ReportTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a report generation task for the authenticated user."""
    task_id = str(uuid4())

    await create_report_task(db, task_id, current_user.id)

    task_input = report_data.model_dump()
    task_input["name"] = task_input.get("name") or current_user.name

    await cache_set(
        f"report:task:{task_id}",
        {"status": "processing", "progress": 0, "message": "Report task queued"},
        expire=600,
    )
    generate_report_task.apply_async(
        args=[current_user.id, task_input],
        task_id=task_id,
    )
    logger.info(f"Report generation task queued | task_id: {task_id}")

    return ReportTaskResponse(
        task_id=task_id,
        status="processing",
        estimated_time=60,
    )


@router.get("/tasks/{task_id}", response_model=ReportTaskStatusResponse)
async def get_report_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get report generation task status."""
    logger.info(f"Report task status requested | task_id: {task_id}")

    task = await get_report_task(db, task_id, current_user.id)
    if not task:
        logger.warning(f"Report task not found | task_id: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    cached_status = await cache_get(f"report:task:{task_id}")
    status_data = json.loads(cached_status) if cached_status else {}

    return ReportTaskStatusResponse(
        task_id=task_id,
        status=task.status,
        report_id=task.report_id,
        progress=task.progress,
        error=task.error or status_data.get("error"),
    )


@router.get("/staff/tasks/{task_id}", response_model=ReportTaskStatusResponse)
async def get_staff_report_task_status(
    task_id: str,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    """Get a report task for an administrator or assigned consultant."""
    task = await get_report_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if current_user.role == "consultant":
        assignment = await db.execute(
            select(Booking.id).where(
                Booking.user_id == task.user_id,
                Booking.consultant_id == current_user.id,
                Booking.status != "cancelled",
            ).limit(1)
        )
        if not assignment.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned")

    cached_status = await cache_get(f"report:task:{task_id}")
    status_data = json.loads(cached_status) if cached_status else {}
    return ReportTaskStatusResponse(
        task_id=task_id,
        status=task.status,
        report_id=task.report_id,
        progress=task.progress,
        error=task.error or status_data.get("error"),
    )


@router.get("", response_model=ReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's reports with pagination."""
    skip = (page - 1) * size
    reports, total = await get_user_reports(db, current_user.id, skip=skip, limit=size)

    return ReportListResponse(total=total, items=format_report_list(reports))


@router.get("/staff/users/{user_id}", response_model=ReportListResponse)
async def get_staff_user_reports(
    user_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "consultant":
        assignment = await db.execute(
            select(Booking.id).where(
                Booking.user_id == user_id,
                Booking.consultant_id == current_user.id,
                Booking.status != "cancelled",
            ).limit(1)
        )
        if not assignment.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned")
    reports, total = await get_user_reports(db, user_id)
    return ReportListResponse(total=total, items=format_report_list(reports))


@router.get("/admin/users/{user_id}", response_model=ReportListResponse)
async def get_admin_user_reports(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    reports, total = await get_user_reports(db, user_id)
    return ReportListResponse(total=total, items=format_report_list(reports))


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get report details."""
    report = await get_report_by_id(db, report_id, current_user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return format_report_response(report)


@router.delete("/{report_id}")
async def delete_report_endpoint(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report."""
    success = await delete_report(db, report_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return {"success": True, "message": "Report deleted successfully"}
