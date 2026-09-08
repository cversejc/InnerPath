from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenResponse,
    RegisterRequest,
    StaffInviteAcceptRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    accept_staff_invite,
    authenticate_with_password,
    create_auth_session,
    register_user,
    revoke_auth_session,
    rotate_auth_session,
)

router = APIRouter()


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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    response: Response,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await register_user(
            db,
            request.phone,
            request.password,
            request.name,
            ip_address=http_request.client.host if http_request.client else None,
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
    return await issue_token_response(db, response, http_request, user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_with_password(db, request.phone, request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")
    if not user.password_hash:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Password setup required")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return await issue_token_response(db, response, http_request, user)


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
        await revoke_auth_session(db, raw_token)
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
    return await issue_token_response(db, response, http_request, user)
