import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    LatestReportContextResponse,
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
from app.services.audit_service import record_audit
from app.services.intake_service import build_intake_snapshot, flatten_snapshot_for_ai, normalize_context
from app.services.service_request_service import has_staff_assignment
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
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a report generation task for the authenticated user."""
    task_id = str(uuid4())

    unified_request = report_data.profile_version is not None or report_data.context is not None
    if unified_request:
        if current_user.profile_completion < 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="请先完成个人档案中的性别和完整出生日期。",
            )
        if report_data.context is not None:
            context = report_data.context.model_dump(exclude_none=False)
        else:
            context = normalize_context(
                selected_topics=report_data.selected_topics,
                additional_info=report_data.additional_info,
            )
        context = normalize_context(context)
        if not context["focus_topics"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少选择一个关注领域。")
        if not context.get("current_challenge"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="请填写当前困惑。")
        if not context["expected_outcomes"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少选择一个期望获得的结果。")
        try:
            snapshot = build_intake_snapshot(
                current_user,
                context,
                request_type="report",
                profile_version=report_data.profile_version,
            )
        except ValueError as error:
            if str(error) == "profile_version_conflict":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="个人档案已更新，请刷新后确认最新资料再提交。",
                )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
        task_input = flatten_snapshot_for_ai(snapshot)
        task_input.update(
            {
                "schema_version": snapshot["schema_version"],
                "profile_version": snapshot["profile_version"],
                "request_type": snapshot["request_type"],
                "profile": snapshot["profile"],
                "context": snapshot["context"],
                "derived": snapshot["derived"],
            }
        )
    else:
        # Legacy clients can continue to submit the original flat payload.
        # Their contact/account fields are still not sent to the AI pipeline.
        task_input = report_data.model_dump(exclude_none=True)
        task_input["name"] = task_input.get("name") or current_user.name
    task_input["name"] = current_user.name if unified_request else task_input.get("name")
    await create_report_task(db, task_id, current_user.id, input_snapshot=task_input)
    await record_audit(
        db,
        current_user.id,
        "report.task.create",
        "report_task",
        task_id,
        target_user_id=current_user.id,
        details={
            "selected_topics": task_input.get("selected_topics", []),
            "profile_version": task_input.get("profile_version"),
            "schema_version": task_input.get("schema_version", 1),
        },
        request=request,
    )
    await db.commit()

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
        if not await has_staff_assignment(db, current_user.id, task.user_id):
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
        if not await has_staff_assignment(db, current_user.id, user_id):
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


@router.get("/latest/context", response_model=LatestReportContextResponse)
async def get_latest_report_context(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id, Report.is_deleted.is_(False))
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if report is None:
        return LatestReportContextResponse()
    snapshot = report.input_snapshot or {}
    context = snapshot.get("context")
    if not context:
        context = normalize_context(
            selected_topics=snapshot.get("selected_topics") or report.selected_topics or [],
            additional_info=snapshot.get("additional_info") or report.additional_info,
        )
    return LatestReportContextResponse(
        report_id=report.id,
        created_at=report.created_at,
        context=context,
    )


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
    request: Request,
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

    await record_audit(
        db,
        current_user.id,
        "report.delete",
        "report",
        str(report_id),
        target_user_id=current_user.id,
        request=request,
    )
    await db.commit()

    return {"success": True, "message": "Report deleted successfully"}
