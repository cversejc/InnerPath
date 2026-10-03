from datetime import date, datetime
from typing import Any, Dict, List, Optional
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


class DecisionLogInput(BaseModel):
    log_date: date
    kind: str = Field("action", pattern="^(action|decision)$")
    status: str = Field("done", pattern="^(done|doing|skipped)$")
    content: str = Field(..., min_length=1, max_length=240)
    note: Optional[str] = Field(None, max_length=240)


class DecisionLogResponse(DecisionLogInput):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DecisionLogListResponse(BaseModel):
    items: List[DecisionLogResponse]


class CalendarCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    meta_payload: Optional[Dict[str, Any]] = None
    entries: List[CalendarEntryInput] = Field(default_factory=list)


class CalendarUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    meta_payload: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")
    entries: Optional[List[CalendarEntryInput]] = None


class CalendarResponse(BaseModel):
    id: int
    user_id: int
    series_id: str
    version_number: int
    is_current: bool = False
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    meta_payload: Optional[Dict[str, Any]] = None
    calendar_request_id: Optional[int] = None
    published_at: Optional[datetime]
    entries: List[CalendarEntryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CalendarImportRequest(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    meta_payload: Optional[Dict[str, Any]] = None
    entries: List[CalendarEntryInput] = Field(..., min_length=1)


class CalendarListResponse(BaseModel):
    items: List[CalendarResponse]


class CalendarRequestCreate(BaseModel):
    profile_version: Optional[int] = Field(None, ge=1)
    source_report_id: Optional[int] = Field(None, ge=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    focus_topics: List[str] = Field(default_factory=list, max_length=3)
    usage_scenario: Optional[str] = Field(None, max_length=50)
    goal: Optional[str] = Field(None, max_length=1000)
    decision_description: Optional[str] = Field(None, max_length=1000)
    expected_outcomes: List[str] = Field(default_factory=list, max_length=7)
    additional_info: Optional[str] = Field(None, max_length=2000)


class CalendarRequestResponse(CalendarRequestCreate):
    id: int
    user_id: int
    status: str
    source_report_id: Optional[int] = None
    calendar_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    generation_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CalendarRequestListResponse(BaseModel):
    items: List[CalendarRequestResponse]


class CalendarRequestAdminUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|reviewing|fulfilled|rejected|cancelled)$")
    review_note: Optional[str] = Field(None, max_length=1000)
    calendar_id: Optional[int] = Field(None, ge=1)
