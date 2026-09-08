from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    gender: Optional[str]
    birth_year: Optional[int]
    birth_month: Optional[int]
    birth_day: Optional[int]
    birth_hour: Optional[int]
    birth_minute: Optional[int]
    birth_place: Optional[str]
    avatar_url: Optional[str]
    user_type: str
    role: str
    is_active: bool
    phone_verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def masked_phone(self) -> str:
        """Return masked phone number"""
        if self.phone and len(self.phone) >= 11:
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        return self.phone
