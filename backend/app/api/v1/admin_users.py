from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import _count, _date_filter
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.calendar import DecisionLog, UserCalendar
from app.models.report import Report
from app.models.user import User
from app.schemas.admin import (
    AdminPasswordResetRequest,
    AdminUserListResponse,
    AdminUserSummaryResponse,
    AdminUserUpdate,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.schemas.calendar import StaffInviteCreate, StaffInviteResponse
from app.schemas.user import UserResponse
from app.services.audit_service import record_audit
from app.services.auth_service import admin_reset_password, create_staff_invite
from app.services.user_service import apply_user_profile_update

router = APIRouter()


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, pattern="^(user|consultant|admin)$"),
    is_active: Optional[bool] = None,
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if search:
        conditions.append(or_(User.name.ilike(f"%{search}%"), User.phone.ilike(f"%{search}%")))
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    conditions.extend(_date_filter(User.created_at, created_from, created_to))

    report_count = select(func.count(Report.id)).where(Report.user_id == User.id, Report.is_deleted.is_(False)).correlate(User).scalar_subquery()
    calendar_count = select(func.count(UserCalendar.id)).where(UserCalendar.user_id == User.id).correlate(User).scalar_subquery()
    count_statement = select(func.count(User.id))
    if conditions:
        count_statement = count_statement.where(*conditions)
    total = await _count(db, count_statement)
    statement = (
        select(User, report_count.label("report_count"), calendar_count.label("calendar_count"))
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if conditions:
        statement = statement.where(*conditions)
    rows = (await db.execute(statement)).all()
    items = [
        {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "user_type": user.user_type,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "report_count": int(report_count_value or 0),
            "calendar_count": int(calendar_count_value or 0),
        }
        for user, report_count_value, calendar_count_value in rows
    ]
    return AdminUserListResponse(total=total, page=page, size=size, items=items)

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

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_profile_by_admin(
    user_id: int,
    data: AdminUserUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if "name" in data.model_fields_set and data.name is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty")
    try:
        changed_fields = apply_user_profile_update(user, data.model_dump(exclude_unset=True))
    except ValueError as error:
        detail_map = {
            "name_required": "请填写称呼。",
            "calendar_type_required": "请选择历法类型。",
            "birth_date_invalid": "出生日期无效，请检查年月日。",
            "birth_time_requires_hour_and_minute": "请同时填写出生时间的小时和分钟。",
            "birth_time_requires_precision": "填写出生时间前，请先选择时间准确度。",
        }
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_map.get(str(error), str(error)),
        )
    if changed_fields:
        await record_audit(
            db,
            current_user.id,
            "user.profile.update.admin",
            "user",
            str(user.id),
            target_user_id=user.id,
            details={"changed_fields": changed_fields, "profile_version": user.profile_version},
            request=request,
        )
        await db.commit()
        await db.refresh(user)
    return user

@router.get("/users/{user_id}/summary", response_model=AdminUserSummaryResponse)
async def get_user_summary(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    report_count = await _count(db, select(func.count(Report.id)).where(Report.user_id == user_id, Report.is_deleted.is_(False)))
    calendar_count = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.user_id == user_id))
    published_calendar_count = await _count(db, select(func.count(UserCalendar.id)).where(UserCalendar.user_id == user_id, UserCalendar.status == "published"))
    decision_log_count = await _count(db, select(func.count(DecisionLog.id)).where(DecisionLog.user_id == user_id))
    return {
        "user": user,
        "summary": {
            "report_count": report_count,
            "calendar_count": calendar_count,
            "published_calendar_count": published_calendar_count,
            "decision_log_count": decision_log_count,
        },
    }

@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    request_data: UserStatusUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.id == user.id and not request_data.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
    if user.role == "admin" and user.is_active and not request_data.is_active:
        active_admins = await _count(db, select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True)))
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the last admin")
    old_status = user.is_active
    user.is_active = request_data.is_active
    await record_audit(
        db,
        current_user.id,
        "user.status.update",
        "user",
        str(user.id),
        target_user_id=user.id,
        details={"old_is_active": old_status, "is_active": user.is_active},
        request=request,
    )
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    request_data: UserRoleUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == "admin" and request_data.role != "admin" and user.is_active:
        active_admins = await _count(db, select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True)))
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the last admin")
    old_role = user.role
    user.role = request_data.role
    await record_audit(
        db,
        current_user.id,
        "user.role.update",
        "user",
        str(user.id),
        target_user_id=user.id,
        details={"old_role": old_role, "new_role": user.role},
        request=request,
    )
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/users/{user_id}/password/reset")
async def reset_user_password_by_admin(
    user_id: int,
    request_data: AdminPasswordResetRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await admin_reset_password(db, user, request_data.new_password)
    await record_audit(db, current_user.id, "user.password.reset", "user", str(user.id), target_user_id=user.id, request=request)
    await db.commit()
    return {"success": True, "message": "Password reset successfully"}

@router.post("/staff/invites", response_model=StaffInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    data: StaffInviteCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    invite, token = await create_staff_invite(db, data.phone, data.role, current_user.id)
    await record_audit(db, current_user.id, "staff.invite.create", "staff_invite", str(invite.id), details={"role": data.role}, request=request)
    await db.commit()
    return StaffInviteResponse(id=invite.id, phone=invite.phone, role=invite.role, token=token, expires_at=invite.expires_at)
