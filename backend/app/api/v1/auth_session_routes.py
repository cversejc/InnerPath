from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.domains.audit.service import record_audit
from app.domains.auth.schemas import LoginRequest, RefreshTokenResponse, TokenResponse
from app.domains.auth.service import authenticate_with_password, revoke_auth_session, rotate_auth_session
from app.api.v1.auth_support import clear_refresh_cookie, issue_token_response, set_refresh_cookie


router = APIRouter()


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
            await record_audit(
                db,
                user_id,
                "auth.logout",
                "user",
                str(user_id),
                target_user_id=user_id,
                audit_context=audit_context_from_request(request),
            )
            await db.commit()
    clear_refresh_cookie(response)
    return {"success": True, "message": "Logged out successfully"}
