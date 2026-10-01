from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import _load_admin_bookings, _serialize_admin_booking
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.booking import Booking
from app.models.user import User
from app.schemas.admin import AdminBookingListResponse, AdminBookingResponse
from app.schemas.booking import BookingAdminUpdate, BookingResponse
from app.services.audit_service import record_audit
from app.services.booking_service import update_booking

router = APIRouter()


@router.get("/bookings", response_model=AdminBookingListResponse)
async def list_admin_bookings(
    booking_status: Optional[str] = Query(None, alias="status", pattern="^(pending|confirmed|completed|cancelled)$"),
    consultant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _load_admin_bookings(db, booking_status=booking_status, consultant_id=consultant_id, user_id=user_id, search=search, date_from=date_from, date_to=date_to, page=page, size=size)
    return AdminBookingListResponse(total=total, page=page, size=size, items=items)

@router.patch("/bookings/{booking_id}", response_model=AdminBookingResponse)
async def update_admin_booking(
    booking_id: int,
    data: BookingAdminUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    before = {field: getattr(booking, field) for field in data.model_dump(exclude_unset=True)}
    try:
        booking = await update_booking(db, booking_id, data, commit=False)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    await record_audit(
        db,
        current_user.id,
        "booking.update",
        "booking",
        str(booking.id),
        target_user_id=booking.user_id,
        details={"before": {key: str(value) for key, value in before.items()}, "changed_fields": list(before.keys())},
        request=request,
    )
    await db.commit()
    await db.refresh(booking)
    user = await db.get(User, booking.user_id)
    return _serialize_admin_booking(booking, user)

@router.get("/users/{user_id}/bookings", response_model=AdminBookingListResponse)
async def list_user_bookings(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    items, total = await _load_admin_bookings(db, user_id=user_id, page=page, size=size)
    return AdminBookingListResponse(total=total, page=page, size=size, items=items)
