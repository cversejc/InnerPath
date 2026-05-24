from pydantic import BaseModel, Field
from typing import Optional


class SendCodeRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")


class SendCodeResponse(BaseModel):
    success: bool
    expires_in: int = 300


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenResponse(BaseModel):
    access_token: str
    expires_in: int


from app.schemas.user import UserResponse
TokenResponse.model_rebuild()
