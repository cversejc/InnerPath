from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate
from app.schemas.booking import BookingAdminUpdate


# Service type mapping
SERVICE_TYPES = {
    "trial": {
        "name": "辰鉴·实践陪伴",
        "price": 99.00
    },
    "basic": {
        "name": "辰鉴·人生说明书",
        "price": 499.00
    },
    "advanced": {
        "name": "辰鉴·行动与决策",
        "price": 1599.00
    }
}


async def create_booking(
    db: AsyncSession,
    user_id: int,
    booking_data: BookingCreate
) -> Booking:
    """Create a new booking"""
    service_info = SERVICE_TYPES.get(booking_data.service_type, SERVICE_TYPES["trial"])

    booking = Booking(
        user_id=user_id,
        service_type=booking_data.service_type,
        service_name=service_info["name"],
        service_price=service_info["price"],
        preferred_time=booking_data.preferred_time,
        contact_phone=booking_data.contact_phone,
        topics=booking_data.topics,
        notes=booking_data.notes,
        status="pending"
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def get_booking_by_id(
    db: AsyncSession,
    booking_id: int,
    user_id: Optional[int] = None
) -> Optional[Booking]:
    """Get booking by ID"""
    query = select(Booking).where(Booking.id == booking_id)
    if user_id:
        query = query.where(Booking.user_id == user_id)

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_bookings(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None
) -> tuple[List[Booking], int]:
    """Get user's bookings"""
    query = select(Booking).where(Booking.user_id == user_id)

    if status:
        query = query.where(Booking.status == status)

    query = query.order_by(desc(Booking.created_at))

    result = await db.execute(query)
    bookings = result.scalars().all()

    return list(bookings), len(bookings)


async def cancel_booking(
    db: AsyncSession,
    booking_id: int,
    user_id: int,
    reason: Optional[str] = None
) -> bool:
    """Cancel a booking"""
    booking = await get_booking_by_id(db, booking_id, user_id)
    if not booking or booking.status == "cancelled":
        return False

    booking.status = "cancelled"
    booking.cancellation_reason = reason
    await db.commit()
    return True


async def get_all_bookings(
    db: AsyncSession,
    status: Optional[str] = None,
    consultant_id: Optional[int] = None,
) -> tuple[List[Booking], int]:
    query = select(Booking)
    if status:
        query = query.where(Booking.status == status)
    if consultant_id:
        query = query.where(Booking.consultant_id == consultant_id)
    query = query.order_by(desc(Booking.created_at))
    result = await db.execute(query)
    bookings = list(result.scalars().all())
    return bookings, len(bookings)


async def update_booking(
    db: AsyncSession,
    booking_id: int,
    booking_update: BookingAdminUpdate,
    consultant_scope: Optional[int] = None,
) -> Optional[Booking]:
    query = select(Booking).where(Booking.id == booking_id)
    if consultant_scope is not None:
        query = query.where(Booking.consultant_id == consultant_scope)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()
    if not booking:
        return None

    update_data = booking_update.model_dump(exclude_unset=True)
    if "consultant_id" in update_data and update_data["consultant_id"] is not None:
        consultant_result = await db.execute(
            select(User).where(User.id == update_data["consultant_id"], User.role == "consultant", User.is_active == True)
        )
        consultant = consultant_result.scalar_one_or_none()
        if not consultant:
            raise ValueError("invalid_consultant")
        booking.consultant_name = consultant.name

    for field, value in update_data.items():
        setattr(booking, field, value)
    if "consultant_id" in update_data and update_data["consultant_id"] is None:
        booking.consultant_name = None

    await db.commit()
    await db.refresh(booking)
    return booking
