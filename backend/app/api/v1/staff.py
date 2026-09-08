from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.booking import BookingAdminUpdate, BookingListResponse, BookingResponse
from app.schemas.calendar import CalendarListResponse
from app.schemas.report import ReportListItem, ReportListResponse, ReportResponse
from app.schemas.user import UserResponse
from app.services.booking_service import get_all_bookings, update_booking
from app.services.calendar_service import get_user_calendars, has_staff_assignment
from app.services.report_service import format_report_response, get_report_by_id, get_user_reports

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


@router.get("/bookings", response_model=BookingListResponse)
async def get_staff_bookings(
    booking_status: Optional[str] = Query(None, alias="status", pattern="^(pending|confirmed|completed|cancelled)$"),
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    consultant_id = current_user.id if current_user.role == "consultant" else None
    bookings, total = await get_all_bookings(db, status=booking_status, consultant_id=consultant_id)
    return BookingListResponse(total=total, items=bookings)


@router.patch("/bookings/{booking_id}", response_model=BookingResponse)
async def update_staff_booking(
    booking_id: int,
    request: BookingAdminUpdate,
    current_user: User = Depends(require_roles("consultant")),
    db: AsyncSession = Depends(get_db),
):
    request_data = request.model_dump(exclude_unset=True, exclude={"consultant_id"})
    try:
        booking = await update_booking(
            db,
            booking_id,
            BookingAdminUpdate(**request_data),
            consultant_scope=current_user.id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid booking update")
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned booking not found")
    return booking
