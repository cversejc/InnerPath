from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.core.logging_config import get_logger
from app.core.sms import (
    SmsCooldownError,
    SmsDeliveryError,
    SmsProviderNotConfigured,
    SmsRateLimitError,
    enforce_sms_rate_limit,
    send_verification_code,
    verify_code,
)
from app.core.security import verify_password
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.domains.audit.service import record_audit
from app.domains.auth.schemas import (
    DeactivateAccountRequest,
    PhoneChangeCodeRequest,
    PhoneChangeRequest,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
    StaffInviteAcceptRequest,
    TokenResponse,
    VerifiedRegisterRequest,
)
from app.domains.auth.service import (
    accept_staff_invite,
    change_user_phone,
    deactivate_user_account,
    register_user,
    reset_password_with_code,
)
from app.domains.users.schemas import UserResponse
from app.models.user import User
from app.api.v1.auth_support import clear_refresh_cookie, issue_token_response


router = APIRouter()
logger = get_logger("app.api.v1.auth")


@router.post("/me/phone-change-code", status_code=status.HTTP_202_ACCEPTED)
async def request_phone_change_code(
    payload: PhoneChangeCodeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.new_phone == current_user.phone:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="新手机号与当前手机号相同")
    result = await db.execute(select(User).where(User.phone == payload.new_phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已绑定其他账号")

    try:
        await enforce_sms_rate_limit(
            payload.new_phone,
            http_request.client.host if http_request.client else None,
        )
        await send_verification_code(payload.new_phone, "phone_change")
    except SmsRateLimitError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="验证码请求过于频繁，请稍后重试")
    except SmsCooldownError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请稍后再获取验证码")
    except SmsProviderNotConfigured:
        logger.warning("Phone change verification failed: SMS provider is not configured")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="短信服务暂不可用")
    except SmsDeliveryError:
        logger.warning("Phone change verification code delivery was rejected by provider")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="验证码发送失败，请稍后重试")

    return {"success": True, "message": "验证码已发送"}


@router.put("/me/phone", response_model=UserResponse)
async def change_phone(
    payload: PhoneChangeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
    if payload.new_phone == current_user.phone:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="新手机号与当前手机号相同")
    if not await verify_code(payload.new_phone, payload.code, "phone_change"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    try:
        user = await change_user_phone(db, current_user, payload.new_phone)
        await record_audit(
            db,
            current_user.id,
            "auth.phone.change",
            "user",
            str(current_user.id),
            target_user_id=current_user.id,
            details={"phone_changed": True},
            audit_context=audit_context_from_request(http_request),
        )
        await db.commit()
        await db.refresh(user)
    except ValueError as error:
        if str(error) == "phone_already_registered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已绑定其他账号") from error
        raise
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已绑定其他账号") from error

    return user


@router.post("/me/deactivate")
async def deactivate_account(
    payload: DeactivateAccountRequest,
    response: Response,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")

    if current_user.role == "admin":
        active_admin_count = await db.scalar(
            select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))
        )
        if int(active_admin_count or 0) <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先确保至少有一名有效管理员账号")

    await deactivate_user_account(db, current_user)
    await record_audit(
        db,
        current_user.id,
        "user.account.self_deactivate",
        "user",
        str(current_user.id),
        target_user_id=current_user.id,
        details={"retained_data": True},
        audit_context=audit_context_from_request(http_request),
    )
    await db.commit()
    clear_refresh_cookie(response)
    return {"success": True, "message": "账号已停用，历史资料仍会保留"}


@router.post("/verification-code", status_code=status.HTTP_202_ACCEPTED)
async def request_verification_code(
    payload: SendVerificationCodeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        await enforce_sms_rate_limit(
            payload.phone,
            http_request.client.host if http_request.client else None,
        )
    except SmsRateLimitError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many code requests")

    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()
    if payload.purpose == "register" and user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")
    if payload.purpose != "register" and not user:
        return {"success": True, "message": "If this phone is registered, a verification code will be sent"}

    try:
        await send_verification_code(payload.phone, payload.purpose)
    except SmsCooldownError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Please wait before requesting another code")
    except SmsProviderNotConfigured:
        logger.warning("SMS verification code request failed: provider is not configured")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SMS service is not configured")
    except SmsDeliveryError as error:
        logger.warning("SMS verification code delivery rejected by provider: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send verification code",
        )

    return {"success": True, "message": "If this phone is registered, a verification code will be sent"}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: VerifiedRegisterRequest,
    response: Response,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not await verify_code(request.phone, request.code, "register"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")

    try:
        user = await register_user(
            db,
            request.phone,
            request.password,
            request.name,
            ip_address=http_request.client.host if http_request.client else None,
            phone_verified=True,
        )
    except ValueError as error:
        if str(error) == "phone_already_registered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")
        if str(error) == "registration_rate_limited":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Registration temporarily limited",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed")
    token_response = await issue_token_response(db, response, http_request, user)
    await record_audit(
        db,
        user.id,
        "auth.register",
        "user",
        str(user.id),
        target_user_id=user.id,
        audit_context=audit_context_from_request(http_request),
    )
    await db.commit()
    return token_response


@router.post("/password/reset")
async def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not await verify_code(request.phone, request.code, "reset"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")

    result = await db.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")

    await reset_password_with_code(db, user, request.new_password)
    await record_audit(
        db,
        user.id,
        "auth.password.reset",
        "user",
        str(user.id),
        target_user_id=user.id,
        audit_context=audit_context_from_request(http_request),
    )
    await db.commit()
    return {"success": True, "message": "Password reset successfully"}


@router.post("/staff/accept-invite", response_model=TokenResponse)
async def accept_invite(
    request: StaffInviteAcceptRequest,
    response: Response,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await accept_staff_invite(
            db,
            request.token,
            request.phone,
            request.password,
            request.name,
        )
    except ValueError as error:
        if str(error) == "phone_already_registered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid staff invite")
    token_response = await issue_token_response(db, response, http_request, user)
    await record_audit(
        db,
        user.id,
        "staff.invite.accept",
        "user",
        str(user.id),
        target_user_id=user.id,
        audit_context=audit_context_from_request(http_request),
    )
    await db.commit()
    return token_response
