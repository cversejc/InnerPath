from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingListResponse,
    BookingCancelRequest,
    BookingCancelResponse
)
from app.services.booking_service import (
    create_booking,
    get_booking_by_id,
    get_user_bookings,
    cancel_booking
)

router = APIRouter()


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_endpoint(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new booking"""
    booking = await create_booking(db, current_user.id, booking_data)
    return booking


@router.get("", response_model=BookingListResponse)
async def get_bookings(
    status: str = Query(None, regex="^(pending|confirmed|completed|cancelled)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's bookings"""
    bookings, total = await get_user_bookings(db, current_user.id, status=status)
    return BookingListResponse(total=total, items=bookings)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get booking details"""
    booking = await get_booking_by_id(db, booking_id, current_user.id)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    return booking


@router.post("/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking_endpoint(
    booking_id: int,
    cancel_request: BookingCancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a booking"""
    success = await cancel_booking(
        db,
        booking_id,
        current_user.id,
        cancel_request.reason
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found or already cancelled"
        )

    return BookingCancelResponse(success=True, message="预约已取消")
