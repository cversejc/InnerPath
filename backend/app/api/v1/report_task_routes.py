import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.user import User
from app.domains.reports.schemas import ReportTaskStatusResponse
from app.domains.reports.task_service import get_report_task, get_report_task_by_id
from app.domains.service_requests.service import has_staff_assignment

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "",
    status_code=status.HTTP_410_GONE,
    deprecated=True,
)
async def create_report(current_user: User = Depends(get_current_active_user)):
    """Retired legacy entry point; new reports require the consultant workflow."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="直接生成报告已停用，请提交报告服务申请，由咨询师协作审核后交付。",
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    if current_user.role == "consultant":
        if not await has_staff_assignment(db, current_user.id, task.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned"
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
