from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.domains.auth.schemas import ChangePasswordRequest
from app.domains.auth.service import change_user_password
from app.domains.users.schemas import UserResponse, UserUpdate
from app.domains.users.service import update_user_profile
from app.domains.audit.service import record_audit

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information"""
    try:
        updated_user = await update_user_profile(db, current_user, user_update)
    except ValueError as error:
        detail_map = {
            "name_required": "请填写称呼",
            "calendar_type_required": "请选择历法类型",
            "birth_date_invalid": "出生日期无效，请检查年月日",
            "birth_time_requires_hour_and_minute": "请同时填写出生时间的小时和分钟",
            "birth_time_requires_precision": "填写出生时间前，请先选择时间准确度",
        }
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_map.get(str(error), str(error)),
        )
    await record_audit(
        db,
        current_user.id,
        "user.profile.update",
        "user",
        str(current_user.id),
        target_user_id=current_user.id,
        details={
            "changed_fields": list(user_update.model_dump(exclude_unset=True).keys()),
            "profile_version": updated_user.profile_version,
        },
        request=request,
    )
    await db.commit()
    return updated_user


@router.post("/me/change-password")
async def change_password(
    request: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await change_user_password(
            db,
            current_user,
            request.current_password,
            request.new_password,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password")
    await record_audit(
        db,
        current_user.id,
        "user.password.change",
        "user",
        str(current_user.id),
        target_user_id=current_user.id,
        request=http_request,
    )
    await db.commit()
    return {"success": True, "message": "Password changed successfully"}
