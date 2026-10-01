from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.db.session import get_db
from app.domains.audit.service import record_audit
from app.domains.auth.schemas import (
    ResetPasswordRequest,
    SendVerificationCodeRequest,
    StaffInviteAcceptRequest,
    TokenResponse,
    VerifiedRegisterRequest,
)
from app.domains.auth.service import accept_staff_invite, register_user, reset_password_with_code
from app.models.user import User
from app.api.v1.auth_support import issue_token_response


router = APIRouter()
logger = get_logger("app.api.v1.auth")


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
        request=http_request,
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
        request=http_request,
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
        request=http_request,
    )
    await db.commit()
    return token_response
