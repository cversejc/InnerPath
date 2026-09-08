from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.user import User
from app.schemas.calendar import CalendarListResponse
from app.services.calendar_service import get_calendar_for_staff, get_user_calendars

router = APIRouter()


@router.get("/me", response_model=CalendarListResponse)
async def get_my_calendars(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    calendars = await get_user_calendars(db, current_user.id, published_only=True)
    return CalendarListResponse(items=calendars)


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
