from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_is_leap_month: bool = False
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    calendar_type: str = Field("solar", pattern="^(solar|lunar)$")
    birth_time_precision: str = Field("unknown", pattern="^(unknown|approximate|exact)$")
    current_residence: Optional[str] = Field(None, max_length=100)
    marital_status: Optional[str] = Field(None, max_length=30)
    occupation_status: Optional[str] = Field(None, max_length=30)
    highest_education: Optional[str] = Field(None, max_length=30)
    mbti: Optional[str] = Field(None, pattern=r"^[A-Za-z]{4}$")
    personality_keywords: List[str] = Field(default_factory=list, max_length=5)
    strengths: Optional[str] = Field(None, max_length=500)
    limitations: Optional[str] = Field(None, max_length=500)
    mingli_experience: List[str] = Field(default_factory=list, max_length=3)
    mingli_experience_other: Optional[str] = Field(None, max_length=500)
    mingli_attitude: Optional[str] = Field(None, max_length=30)
    preferred_content_depth: Optional[str] = Field(None, max_length=30)
    default_usage_scenarios: List[str] = Field(default_factory=list, max_length=6)
    default_usage_scenarios_other: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_is_leap_month: Optional[bool] = None
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    calendar_type: Optional[str] = Field(None, pattern="^(solar|lunar)$")
    birth_time_precision: Optional[str] = Field(None, pattern="^(unknown|approximate|exact)$")
    current_residence: Optional[str] = Field(None, max_length=100)
    marital_status: Optional[str] = Field(None, max_length=30)
    occupation_status: Optional[str] = Field(None, max_length=30)
    highest_education: Optional[str] = Field(None, max_length=30)
    mbti: Optional[str] = Field(None, pattern=r"^[A-Za-z]{4}$")
    personality_keywords: Optional[List[str]] = Field(None, max_length=5)
    strengths: Optional[str] = Field(None, max_length=500)
    limitations: Optional[str] = Field(None, max_length=500)
    mingli_experience: Optional[List[str]] = Field(None, max_length=3)
    mingli_experience_other: Optional[str] = Field(None, max_length=500)
    mingli_attitude: Optional[str] = Field(None, max_length=30)
    preferred_content_depth: Optional[str] = Field(None, max_length=30)
    default_usage_scenarios: Optional[List[str]] = Field(None, max_length=6)
    default_usage_scenarios_other: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    gender: Optional[str]
    birth_year: Optional[int]
    birth_month: Optional[int]
    birth_day: Optional[int]
    birth_is_leap_month: bool
    birth_hour: Optional[int]
    birth_minute: Optional[int]
    birth_place: Optional[str]
    calendar_type: str
    birth_time_precision: str
    current_residence: Optional[str]
    marital_status: Optional[str]
    occupation_status: Optional[str]
    highest_education: Optional[str]
    mbti: Optional[str]
    personality_keywords: List[str]
    strengths: Optional[str]
    limitations: Optional[str]
    mingli_experience: List[str]
    mingli_experience_other: Optional[str] = None
    mingli_attitude: Optional[str]
    preferred_content_depth: Optional[str]
    default_usage_scenarios: List[str]
    default_usage_scenarios_other: Optional[str] = None
    profile_version: int
    profile_last_confirmed_at: Optional[datetime]
    profile_completion: int
    avatar_url: Optional[str]
    user_type: str
    role: str
    consultant_type: Optional[str] = None
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


class LunarMonthOption(BaseModel):
    value: int
    label: str
    day_count: int
    max_day: int


class LunarCalendarOptionYear(BaseModel):
    value: int
    label: str
    months: list[LunarMonthOption]


class LunarCalendarOptionsResponse(BaseModel):
    max_year: int
    years: list[LunarCalendarOptionYear]
