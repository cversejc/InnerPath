from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal


class BookingCreate(BaseModel):
    service_type: str = Field(..., pattern="^(trial|basic|advanced)$")
    preferred_time: str = Field(..., min_length=1, max_length=50)
    contact_phone: str = Field(..., min_length=11, max_length=20)
    topics: List[str] = Field(..., min_items=1)
    notes: Optional[str] = None


class BookingResponse(BaseModel):
    id: int
    service_name: str
    service_type: str
    service_price: Optional[Decimal]
    preferred_time: str
    confirmed_date: Optional[date]
    confirmed_time: Optional[time]
    consultant_name: Optional[str]
    contact_phone: str
    topics: List[str]
    notes: Optional[str]
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
