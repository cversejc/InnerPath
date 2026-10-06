from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.domains.calendar.schemas import CalendarListResponse
from app.domains.reports.schemas import ReportListResponse, ReportResponse
from app.domains.users.schemas import UserResponse
from app.domains.calendar.query_service import get_user_calendars
from app.domains.reports.service import (
    format_report_list_item,
    format_report_response,
    get_report_by_id,
    get_user_reports,
)
from app.domains.service_requests.service import has_staff_assignment

router = APIRouter()


async def ensure_staff_user_access(
    db: AsyncSession,
    current_user: User,
    user_id: int,
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.role == "consultant" and not await has_staff_assignment(db, current_user.id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned")
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_staff_user(
    user_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    return await ensure_staff_user_access(db, current_user, user_id)


@router.get("/users/{user_id}/calendar", response_model=CalendarListResponse)
async def get_staff_calendar(
    user_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await ensure_staff_user_access(db, current_user, user_id)
    return CalendarListResponse(items=await get_user_calendars(db, user_id, published_only=True))


@router.get("/users/{user_id}/reports", response_model=ReportListResponse)
async def get_staff_reports(
    user_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await ensure_staff_user_access(db, current_user, user_id)
    reports, total = await get_user_reports(db, user_id)
    items = [format_report_list_item(report) for report in reports]
    return ReportListResponse(total=total, items=items)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_staff_report(
    report_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    report = await get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await ensure_staff_user_access(db, current_user, report.user_id)
    return format_report_response(report)
