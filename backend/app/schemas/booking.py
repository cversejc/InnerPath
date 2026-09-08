from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal


class BookingCreate(BaseModel):
    service_type: str = Field(..., pattern="^(trial|basic|advanced)$")
    preferred_time: str = Field(..., min_length=1, max_length=50)
    contact_phone: str = Field(..., min_length=11, max_length=20, pattern=r"^\d{11,20}$")
    topics: List[str] = Field(..., min_items=1)
    notes: Optional[str] = None


class BookingResponse(BaseModel):
    id: int
    user_id: int
    service_name: str
    service_type: str
    service_price: Optional[Decimal]
    preferred_time: str
    confirmed_date: Optional[date]
    confirmed_time: Optional[time]
    consultant_name: Optional[str]
    consultant_id: Optional[int]
    contact_phone: str
    topics: List[str]
    notes: Optional[str]
    meeting_url: Optional[str]
    meeting_notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    total: int
    items: List[BookingResponse]


class BookingCancelRequest(BaseModel):
    reason: Optional[str] = None


class BookingCancelResponse(BaseModel):
    success: bool
    message: str = "预约已取消"


class BookingAdminUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|confirmed|completed|cancelled)$")
    confirmed_date: Optional[date] = None
    confirmed_time: Optional[time] = None
    consultant_id: Optional[int] = None
    meeting_url: Optional[str] = Field(None, max_length=255)
    meeting_notes: Optional[str] = None
