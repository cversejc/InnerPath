from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SendVerificationCodeRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$", description="手机号")
    purpose: Literal["register", "reset"]


class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="短信验证码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$", description="手机号")
    password: str = Field(..., min_length=8, max_length=128, description="密码")


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$", description="手机号")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    name: str = Field(..., min_length=1, max_length=50, description="昵称")


class VerifiedRegisterRequest(RegisterRequest):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="短信验证码")


class StaffInviteAcceptRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=50)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PhoneChangeCodeRequest(BaseModel):
    new_phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")


class PhoneChangeRequest(PhoneChangeCodeRequest):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    current_password: str = Field(..., min_length=8, max_length=128)


class DeactivateAccountRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class StaffInviteCreate(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    role: str = Field(..., pattern="^(admin|consultant)$")


class StaffInviteResponse(BaseModel):
    id: int
    phone: str
    role: str
    token: str
    expires_at: datetime


from app.domains.users.schemas import UserResponse
TokenResponse.model_rebuild()
