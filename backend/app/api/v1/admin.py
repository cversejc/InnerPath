from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.calendar import UserCalendar
from app.models.user import AuditLog, User
from app.schemas.admin import (
    AdminPasswordResetRequest,
    AuditLogListResponse,
    AdminUserListResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.schemas.booking import BookingAdminUpdate, BookingListResponse, BookingResponse
from app.schemas.calendar import (
    CalendarCreate,
    CalendarImportRequest,
    CalendarListResponse,
    CalendarResponse,
    CalendarUpdate,
    StaffInviteCreate,
    StaffInviteResponse,
)
from app.schemas.course import UserCourseProgressUpdate
from app.schemas.user import UserResponse
from app.services.auth_service import admin_reset_password, create_staff_invite
from app.services.booking_service import get_all_bookings, update_booking
from app.services.calendar_service import (
    archive_calendar,
    create_calendar,
    get_user_calendars,
    publish_calendar,
    record_audit,
    serialize_calendar,
    update_calendar,
)

router = APIRouter()


async def get_calendar_or_404(db: AsyncSession, calendar_id: int) -> UserCalendar:
    calendar = await db.get(UserCalendar, calendar_id)
    if not calendar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return calendar


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, pattern="^(user|consultant|admin)$"),
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    count_query = select(func.count(User.id))
    if search:
        condition = (User.name.ilike(f"%{search}%")) | (User.phone.ilike(f"%{search}%"))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size))
    return AdminUserListResponse(total=total, items=list(result.scalars().all()))


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    return AuditLogListResponse(total=total, items=list(result.scalars().all()))


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    request: UserStatusUpdate,
    http_request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.id == user.id and not request.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
    if user.role == "admin" and user.is_active and not request.is_active:
        active_admins = await db.execute(
            select(func.count(User.id)).where(User.role == "admin", User.is_active == True)
        )
        if active_admins.scalar_one() <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the last admin")
    user.is_active = request.is_active
    await record_audit(
        db,
        current_user.id,
        "user.status.update",
        "user",
        str(user.id),
        {"is_active": request.is_active, "ip": http_request.client.host if http_request.client else None},
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    request: UserRoleUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == "admin" and request.role != "admin" and user.is_active:
        active_admins = await db.execute(
            select(func.count(User.id)).where(User.role == "admin", User.is_active == True)
        )
        if active_admins.scalar_one() <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the last admin")
    old_role = user.role
    user.role = request.role
    await record_audit(
        db,
        current_user.id,
        "user.role.update",
        "user",
        str(user.id),
        {"old_role": old_role, "new_role": request.role},
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/password/reset")
async def reset_user_password_by_admin(
    user_id: int,
    request: AdminPasswordResetRequest,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await admin_reset_password(db, user, request.new_password)
    await record_audit(db, current_user.id, "user.password.reset", "user", str(user.id))
    await db.commit()
    return {"success": True, "message": "Password reset successfully"}


@router.post("/staff/invites", response_model=StaffInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    request: StaffInviteCreate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    invite, token = await create_staff_invite(db, request.phone, request.role, current_user.id)
    await record_audit(db, current_user.id, "staff.invite.create", "staff_invite", str(invite.id))
    await db.commit()
    return StaffInviteResponse(
        id=invite.id,
        phone=invite.phone,
        role=invite.role,
        token=token,
        expires_at=invite.expires_at,
    )


@router.get("/users/{user_id}/calendars", response_model=CalendarListResponse)
async def list_user_calendars(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return CalendarListResponse(items=await get_user_calendars(db, user_id, published_only=False))


@router.post("/users/{user_id}/calendars", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_user_calendar(
    user_id: int,
    request: CalendarCreate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    calendar = await create_calendar(db, user_id, current_user.id, request)
    return await serialize_calendar(db, calendar)


@router.post("/calendars/import", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def import_calendar(
    request: CalendarImportRequest,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(User, request.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    calendar = await create_calendar(
        db,
        request.user_id,
        current_user.id,
        CalendarCreate(title=request.title, entries=request.entries),
    )
    return await serialize_calendar(db, calendar)


@router.put("/calendars/{calendar_id}", response_model=CalendarResponse)
async def update_user_calendar(
    calendar_id: int,
    request: CalendarUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await get_calendar_or_404(db, calendar_id)
    try:
        calendar = await update_calendar(db, calendar, current_user.id, request)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the publish or archive endpoint to change calendar status",
        )
    return await serialize_calendar(db, calendar)


@router.post("/calendars/{calendar_id}/publish", response_model=CalendarResponse)
async def publish_user_calendar(
    calendar_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await get_calendar_or_404(db, calendar_id)
    try:
        calendar = await publish_calendar(db, calendar, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Calendar must contain entries")
    return await serialize_calendar(db, calendar)


@router.post("/calendars/{calendar_id}/archive", response_model=CalendarResponse)
async def archive_user_calendar(
    calendar_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    calendar = await get_calendar_or_404(db, calendar_id)
    calendar = await archive_calendar(db, calendar, current_user.id)
    return await serialize_calendar(db, calendar)


@router.get("/bookings", response_model=BookingListResponse)
async def list_admin_bookings(
    booking_status: Optional[str] = Query(None, alias="status", pattern="^(pending|confirmed|completed|cancelled)$"),
    consultant_id: Optional[int] = None,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    bookings, total = await get_all_bookings(db, status=booking_status, consultant_id=consultant_id)
    return BookingListResponse(total=total, items=bookings)


@router.patch("/bookings/{booking_id}", response_model=BookingResponse)
async def update_admin_booking(
    booking_id: int,
    request: BookingAdminUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        booking = await update_booking(db, booking_id, request)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid consultant")
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    await record_audit(db, current_user.id, "booking.update", "booking", str(booking.id))
    await db.commit()
    return booking


@router.get("/staff/bookings", response_model=BookingListResponse)
async def list_staff_bookings(
    booking_status: Optional[str] = Query(None, alias="status", pattern="^(pending|confirmed|completed|cancelled)$"),
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    consultant_id = current_user.id if current_user.role == "consultant" else None
    bookings, total = await get_all_bookings(db, status=booking_status, consultant_id=consultant_id)
    return BookingListResponse(total=total, items=bookings)


@router.patch("/staff/bookings/{booking_id}", response_model=BookingResponse)
async def update_staff_booking(
    booking_id: int,
    request: BookingAdminUpdate,
    current_user: User = Depends(require_roles("consultant")),
    db: AsyncSession = Depends(get_db),
):
    update_data = request.model_dump(exclude_unset=True, exclude={"consultant_id"})
    try:
        booking = await update_booking(
            db,
            booking_id,
            BookingAdminUpdate(**update_data),
            consultant_scope=current_user.id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid booking update")
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned booking not found")
    await record_audit(db, current_user.id, "booking.staff.update", "booking", str(booking.id))
    await db.commit()
    return booking


@router.get("/courses/users/{user_id}")
async def list_user_courses(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.course_service import get_user_courses

    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"items": await get_user_courses(db, user_id)}


@router.patch("/courses/users/{user_id}/{course_id}/progress")
async def update_user_course_progress_for_admin(
    user_id: int,
    course_id: int,
    request: UserCourseProgressUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.course_service import update_course_progress_for_admin

    try:
        user_course = await update_course_progress_for_admin(db, user_id, course_id, request)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await record_audit(db, current_user.id, "course.progress.update", "user_course", str(user_course.id))
    await db.commit()
    return {
        "course_id": user_course.course_id,
        "user_id": user_course.user_id,
        "progress": user_course.progress_percentage,
        "completed_lessons": user_course.completed_lessons,
        "status": user_course.status,
    }
