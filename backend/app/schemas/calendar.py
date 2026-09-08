from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CalendarEntryInput(BaseModel):
    entry_date: date
    day_pillar: Optional[str] = Field(None, max_length=20)
    tone: Optional[str] = Field(None, max_length=20)
    status_label: Optional[str] = Field(None, max_length=100)
    keyword: Optional[str] = Field(None, max_length=100)
    summary: Optional[str] = None
    suitable: List[str] = Field(default_factory=list)
    unsuitable: List[str] = Field(default_factory=list)
    time_window: Optional[str] = None
    admin_note: Optional[str] = None


class CalendarEntryResponse(CalendarEntryInput):
    id: int

    class Config:
        from_attributes = True


class CalendarCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    entries: List[CalendarEntryInput] = Field(default_factory=list)


class CalendarUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")
    entries: Optional[List[CalendarEntryInput]] = None


class CalendarResponse(BaseModel):
    id: int
    user_id: int
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    published_at: Optional[datetime]
    entries: List[CalendarEntryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CalendarImportRequest(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=150)
    entries: List[CalendarEntryInput] = Field(..., min_length=1)


class CalendarListResponse(BaseModel):
    items: List[CalendarResponse]


class StaffInviteCreate(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    role: str = Field(..., pattern="^(admin|consultant)$")


class StaffInviteResponse(BaseModel):
    id: int
    phone: str
    role: str
    token: str
    expires_at: datetime
