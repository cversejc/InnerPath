import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.dependencies import get_current_active_user
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
    delete_report,
    format_report_response,
    get_report_by_id,
    get_user_reports,
)
from app.tasks.report_tasks import generate_report_task

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=ReportTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_report(report_data: ReportCreate):
    """Create a report generation task for guest users."""
    # The API only queues the job. The Celery worker owns the slow AI call,
    # persistence, and final task status updates.
    user_id = None
    task_id = str(uuid4())

    await cache_set(
        f"report:task:{task_id}",
        {"status": "processing", "progress": 0, "message": "Report task queued"},
        expire=600,
    )
    generate_report_task.apply_async(
        args=[user_id, report_data.model_dump()],
        task_id=task_id,
    )
    logger.info(f"Report generation task queued | task_id: {task_id}")

    return ReportTaskResponse(
        task_id=task_id,
        status="processing",
        estimated_time=60,
    )


@router.get("/tasks/{task_id}", response_model=ReportTaskStatusResponse)
async def get_report_task_status(task_id: str):
    """Get report generation task status."""
    logger.info(f"Report task status requested | task_id: {task_id}")

    cached_status = await cache_get(f"report:task:{task_id}")
    if not cached_status:
        logger.warning(f"Report task not found | task_id: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    status_data = json.loads(cached_status)
    report_data = status_data.get("report_data")

    return ReportTaskStatusResponse(
        task_id=task_id,
        status=status_data.get("status", "processing"),
        report_id=status_data.get("report_id"),
        report_data=report_data,
        progress=status_data.get("progress", 0),
        error=status_data.get("error"),
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

    items = []
    for report in reports:
        energy_type = report.energy_profile.get("type") if report.energy_profile else None
        core_traits = report.energy_profile.get("core_traits") if report.energy_profile else None

        items.append(
            ReportListItem(
                id=report.id,
                title=report.title,
                created_at=report.created_at,
                energy_type=energy_type,
                core_traits=core_traits,
            )
        )

    return ReportListResponse(total=total, items=items)


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
