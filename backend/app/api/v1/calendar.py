from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.user import User
from app.schemas.calendar import (
    DecisionLogInput,
    DecisionLogListResponse,
    DecisionLogResponse,
    CalendarListResponse,
)
from app.services.calendar_service import (
    create_user_decision_log,
    delete_user_decision_log,
    get_calendar_for_staff,
    get_user_calendars,
    get_user_decision_logs,
)

router = APIRouter()


@router.get("/me", response_model=CalendarListResponse)
async def get_my_calendars(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    calendars = await get_user_calendars(db, current_user.id, published_only=True)
    return CalendarListResponse(items=calendars)


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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_user_decision_log(db, current_user.id, data)


@router.delete("/decision-logs/{log_id}")
async def delete_my_decision_log(
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_user_decision_log(db, current_user.id, log_id)
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
