from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.user import User
from app.domains.calendar.schemas import (
    CalendarRequestCreate,
    CalendarRequestListResponse,
    CalendarRequestResponse,
    DecisionLogInput,
    DecisionLogListResponse,
    DecisionLogResponse,
    CalendarListResponse,
)
from app.domains.calendar.models import CalendarRequest
from app.domains.calendar.query_service import get_user_calendars
from app.domains.calendar.decision_logs import (
    create_user_decision_log,
    delete_user_decision_log,
    get_user_decision_logs,
)
from app.application.staff_calendar_access import get_calendar_for_staff
from app.domains.calendar.requests import (
    create_calendar_request,
    get_user_calendar_requests,
    retry_calendar_generation,
    serialize_calendar_request,
)
from app.tasks.calendar_generation_dispatch import dispatch_calendar_generation

router = APIRouter()


@router.get("/me", response_model=CalendarListResponse)
async def get_my_calendars(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    calendars = await get_user_calendars(
        db,
        current_user.id,
        published_only=True,
        include_internal=False,
    )
    return CalendarListResponse(items=calendars)


@router.post("/requests", response_model=CalendarRequestResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_my_calendar_request(
    data: CalendarRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        calendar_request = await create_calendar_request(
            db,
            current_user,
            data,
            audit_context=audit_context_from_request(request),
        )
    except ValueError as error:
        message_map = {
            "profile_version_conflict": "个人档案已更新，请刷新后确认最新资料再提交",
            "calendar_request_profile_incomplete": "请先完成个人档案中的性别和完整出生日期",
            "calendar_request_requires_date_range": "请选择完整的日历周期",
            "invalid_calendar_range": "日历开始日期不能晚于结束日期",
            "calendar_request_requires_focus_topics": "至少选择一个关注领域",
            "calendar_request_requires_usage_scenario": "请选择日历用途",
            "calendar_request_requires_goal": "请填写当前决策目标",
            "calendar_request_requires_expected_outcomes": "至少选择一个期望输出",
            "calendar_request_source_report_required": "请先申请报告，并等待咨询师交付后再生成日历。",
            "calendar_request_source_report_not_delivered": "请先申请报告，并等待咨询师交付后再生成日历。",
            "calendar_request_must_cover_30_days": "日历周期需覆盖 30 天，请重新选择日期。",
        }
        code = status.HTTP_409_CONFLICT if str(error) == "profile_version_conflict" else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=message_map.get(str(error), str(error)))
    try:
        dispatch_calendar_generation(calendar_request.id, calendar_request.task_id)
    except Exception:
        calendar_request.status = "failed"
        calendar_request.progress = 0
        calendar_request.generation_error = "日历任务暂时无法启动，请稍后重试。"
        await db.commit()
        await db.refresh(calendar_request)
    return await serialize_calendar_request(db, calendar_request)


@router.get("/requests", response_model=CalendarRequestListResponse)
async def get_my_calendar_requests(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return CalendarRequestListResponse(items=await get_user_calendar_requests(db, current_user.id))


@router.post("/requests/{request_id}/retry", response_model=CalendarRequestResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_my_calendar_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    calendar_request = await db.get(CalendarRequest, request_id)
    if not calendar_request or calendar_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar request not found")
    try:
        calendar_request = await retry_calendar_generation(
            db,
            calendar_request,
            current_user,
            audit_context=audit_context_from_request(request),
        )
    except ValueError as error:
        code = str(error)
        if code == "calendar_request_source_report_not_delivered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先申请报告，并等待咨询师交付后再生成日历。")
        if code == "calendar_request_retry_not_allowed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前日历任务不能重试。")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar request not found")
    try:
        dispatch_calendar_generation(calendar_request.id, calendar_request.task_id)
    except Exception:
        calendar_request.status = "failed"
        calendar_request.progress = 0
        calendar_request.generation_error = "日历任务暂时无法启动，请稍后重试。"
        await db.commit()
        await db.refresh(calendar_request)
    return await serialize_calendar_request(db, calendar_request)


@router.get("/decision-logs", response_model=DecisionLogListResponse)
async def get_my_decision_logs(
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    logs = await get_user_decision_logs(db, current_user.id, start_date, end_date)
    return DecisionLogListResponse(items=logs)


@router.post("/decision-logs", response_model=DecisionLogResponse, status_code=status.HTTP_201_CREATED)
async def create_my_decision_log(
    data: DecisionLogInput,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_user_decision_log(db, current_user.id, data, audit_context=audit_context_from_request(request))


@router.delete("/decision-logs/{log_id}")
async def delete_my_decision_log(
    log_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_user_decision_log(
        db,
        current_user.id,
        log_id,
        audit_context=audit_context_from_request(request),
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision log not found")
    return {"ok": True}


@router.get("/staff/users/{user_id}", response_model=CalendarListResponse)
async def get_assigned_user_calendars(
    user_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "admin":
        calendars = await get_user_calendars(db, user_id, published_only=True)
    else:
        calendars = await get_calendar_for_staff(db, current_user.id, user_id)
    return CalendarListResponse(items=calendars)
