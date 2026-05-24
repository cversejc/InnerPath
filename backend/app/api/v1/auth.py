from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.auth import SendCodeRequest, SendCodeResponse, LoginRequest, TokenResponse
from app.core.sms import send_verification_code
from app.services.auth_service import authenticate_user
from app.core.security import create_access_token
from app.config import settings
from datetime import timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(request: SendCodeRequest):
    """Send SMS verification code"""
    success = await send_verification_code(request.phone)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )

    return SendCodeResponse(success=True, expires_in=300)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login or register with phone and SMS code"""
    user = await authenticate_user(db, request.phone, request.code)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "name": user.name,
            "phone": user.masked_phone,
            "gender": user.gender,
            "user_type": user.user_type,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    )


@router.post("/logout")
async def logout():
    """Logout (client should delete token)"""
    return {"success": True, "message": "Logged out successfully"}
