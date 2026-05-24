from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportTaskResponse,
    ReportTaskStatusResponse,
    ReportListResponse,
    ReportResponse,
    ReportListItem
)
from app.services.report_service import (
    get_report_by_id,
    get_user_reports,
    delete_report,
    format_report_response
)
from app.tasks.report_tasks import generate_report_task
from app.core.logging_config import get_logger
from app.core.cache import cache_get, cache_set
import json

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=ReportTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    report_data: ReportCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new report - No authentication required for guest users"""
    import uuid
    import time
    import logging
    from app.services.ai_service import generate_report_with_ai
    from app.services.report_service import create_report as create_report_db

    logger = logging.getLogger(__name__)

    # For guest users, use user_id = None
    user_id = None

    # Generate a task ID for tracking
    task_id = str(uuid.uuid4())

    logger.info(f"开始生成报告，task_id: {task_id}")

    # Store initial status in cache
    await cache_set(f"report:task:{task_id}", json.dumps({
        "status": "processing",
        "progress": 10
    }), expire=600)

    try:
        # Generate report synchronously (no Celery needed)
        logger.info(f"调用 AI 生成报告...")
        start_time = time.time()
        report_data_dict = await generate_report_with_ai(report_data.model_dump())
        generation_time_ms = int((time.time() - start_time) * 1000)

        logger.info(f"报告生成完成，耗时: {generation_time_ms}ms")
        logger.info(f"报告数据键: {list(report_data_dict.keys())}")

        # Update progress
        await cache_set(f"report:task:{task_id}", json.dumps({
            "status": "processing",
            "progress": 70
        }), expire=600)

        # Save to database only if user is authenticated
        report_id = None
        if user_id:
            report = await create_report_db(
                db,
                user_id=user_id,
                report_data=report_data_dict,
                generation_time_ms=generation_time_ms
            )
            report_id = report.id
            logger.info(f"报告已保存到数据库，report_id: {report_id}")

        # For guest users, store report data in cache temporarily
        if not user_id:
            await cache_set(
                f"report:guest:{task_id}",
                json.dumps(report_data_dict, default=str),
                expire=3600  # 1 hour
            )
            logger.info(f"游客报告已缓存，task_id: {task_id}")

        # Update final status - serialize report_data properly
        status_data = {
            "status": "completed",
            "progress": 100,
            "report_id": report_id
        }

        # Add report_data for guest users
        if not user_id and report_data_dict:
            status_data["report_data"] = report_data_dict
            logger.info(f"报告数据已添加到状态响应")

        await cache_set(f"report:task:{task_id}", json.dumps(status_data, default=str), expire=600)

        logger.info(f"任务状态已更新为 completed")

    except Exception as e:
        logger.error(f"报告生成失败: {str(e)}", exc_info=True)
        # Update failed status
        await cache_set(f"report:task:{task_id}", json.dumps({
            "status": "failed",
            "progress": 0,
            "error": str(e)
        }), expire=600)

    return ReportTaskResponse(
        task_id=task_id,
        status="processing",
        estimated_time=5
    )


@router.get("/tasks/{task_id}", response_model=ReportTaskStatusResponse)
async def get_report_task_status(task_id: str):
    """Get report generation task status"""
    logger.info(f"查询任务状态 | task_id: {task_id}")

    # Check cache for task status
    cached_status = await cache_get(f"report:task:{task_id}")

    if not cached_status:
        logger.warning(f"任务未找到 | task_id: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    status_data = json.loads(cached_status)
    logger.debug(f"任务状态数据 | 包含字段: {list(status_data.keys())}")

    # Check if report_data exists in status
    report_data = status_data.get("report_data")
    if report_data:
        logger.info(f"任务状态包含报告数据 | 数据大小: {len(json.dumps(report_data))} 字符")
    else:
        logger.warning(f"任务状态不包含报告数据")

    return ReportTaskStatusResponse(
        task_id=task_id,
        status=status_data.get("status", "processing"),
        report_id=status_data.get("report_id"),
        report_data=report_data,  # 添加 report_data
        progress=status_data.get("progress", 0),
        error=status_data.get("error")
    )


@router.get("", response_model=ReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's reports with pagination"""
    skip = (page - 1) * size
    reports, total = await get_user_reports(db, current_user.id, skip=skip, limit=size)

    items = []
    for report in reports:
        energy_type = report.energy_profile.get("type") if report.energy_profile else None
        core_traits = report.energy_profile.get("core_traits") if report.energy_profile else None

        items.append(ReportListItem(
            id=report.id,
            title=report.title,
            created_at=report.created_at,
            energy_type=energy_type,
            core_traits=core_traits
        ))

    return ReportListResponse(total=total, items=items)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get report details"""
    report = await get_report_by_id(db, report_id, current_user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return format_report_response(report)


@router.delete("/{report_id}")
async def delete_report_endpoint(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a report"""
    success = await delete_report(db, report_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return {"success": True, "message": "Report deleted successfully"}
