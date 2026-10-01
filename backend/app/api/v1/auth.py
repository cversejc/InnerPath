from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.sms import (
    SmsCooldownError,
    SmsDeliveryError,
    SmsProviderNotConfigured,
    SmsRateLimitError,
    enforce_sms_rate_limit,
    send_verification_code,
    verify_code,
)
from app.core.security import create_access_token
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.user import User
from app.domains.auth.schemas import (
    LoginRequest,
    ResetPasswordRequest,
    RefreshTokenResponse,
    SendVerificationCodeRequest,
    StaffInviteAcceptRequest,
    TokenResponse,
    VerifiedRegisterRequest,
)
from app.domains.users.schemas import UserResponse
from app.domains.auth.service import (
    accept_staff_invite,
    authenticate_with_password,
    create_auth_session,
    register_user,
    reset_password_with_code,
    revoke_auth_session,
    rotate_auth_session,
)
from app.domains.audit.service import record_audit

router = APIRouter()
logger = get_logger(__name__)


def serialize_user(user) -> UserResponse:
    return UserResponse.model_validate(user)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )


async def issue_token_response(
    db: AsyncSession,
    response: Response,
    request: Request,
    user,
) -> TokenResponse:
    refresh_token = await create_auth_session(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_refresh_cookie(response, refresh_token)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=serialize_user(user),
    )


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


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_with_password(db, request.phone, request.password)
    if not user:
        await record_audit(
            db,
            None,
            "auth.login.failure",
            "auth",
            details={"reason": "invalid_credentials"},
            request=http_request,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")
    if not user.password_hash:
        await record_audit(
            db,
            None,
            "auth.login.failure",
            "auth",
            target_user_id=user.id,
            details={"reason": "password_setup_required"},
            request=http_request,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Password setup required")
    if not user.is_active:
        await record_audit(
            db,
            None,
            "auth.login.failure",
            "auth",
            target_user_id=user.id,
            details={"reason": "inactive_user"},
            request=http_request,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    token_response = await issue_token_response(db, response, http_request, user)
    await record_audit(
        db,
        user.id,
        "auth.login.success",
        "user",
        str(user.id),
        target_user_id=user.id,
        request=http_request,
    )
    await db.commit()
    return token_response


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session required")
    result = await rotate_auth_session(db, raw_token)
    if not result:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session expired")
    user, new_refresh_token = result
    set_refresh_cookie(response, new_refresh_token)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return RefreshTokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if raw_token:
        user_id = await revoke_auth_session(db, raw_token)
        if user_id:
            await record_audit(db, user_id, "auth.logout", "user", str(user_id), target_user_id=user_id, request=request)
            await db.commit()
    clear_refresh_cookie(response)
    return {"success": True, "message": "Logged out successfully"}


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
