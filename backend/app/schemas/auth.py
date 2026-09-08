from pydantic import BaseModel, Field
class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$", description="手机号")
    password: str = Field(..., min_length=8, max_length=128, description="密码")


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$", description="手机号（仅作为登录账号）")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    name: str = Field(..., min_length=1, max_length=50, description="昵称")


class StaffInviteAcceptRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=50)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


from app.schemas.user import UserResponse
TokenResponse.model_rebuild()
