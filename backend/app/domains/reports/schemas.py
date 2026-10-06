from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.domains.users.lunar_calendar import solar_date_for_birth


class ReportContext(BaseModel):
    """Per-request context; deliberately separate from the reusable profile."""

    focus_topics: List[str] = Field(default_factory=list, max_length=3)
    current_challenge: Optional[str] = Field(None, max_length=2000)
    expected_outcomes: List[str] = Field(default_factory=list, max_length=7)
    issue_duration: Optional[str] = Field(None, max_length=50)
    impact_level: Optional[str] = Field(None, max_length=50)
    decision_status: Optional[str] = Field(None, max_length=50)
    decision_description: Optional[str] = Field(None, max_length=1000)
    decision_style: List[str] = Field(default_factory=list, max_length=6)
    additional_info: Optional[str] = Field(None, max_length=2000)


class ReportCreate(BaseModel):
    # Legacy flat fields remain optional so older clients can continue to call
    # POST /reports. New clients should provide profile_version + context.
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_is_leap_month: bool = False
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    calendar_type: str = Field("solar", pattern="^(solar|lunar)$")
    selected_topics: List[str] = Field(default_factory=list)
    additional_info: Optional[str] = Field(None, max_length=2000)
    profile_version: Optional[int] = Field(None, ge=1)
    context: Optional[ReportContext] = None

    @model_validator(mode="after")
    def validate_birth_date(self):
        birth_values = (self.birth_year, self.birth_month, self.birth_day)
        if all(value is not None for value in birth_values):
            solar_date_for_birth(
                self.birth_year,
                self.birth_month,
                self.birth_day,
                calendar_type=self.calendar_type,
                is_leap_month=self.birth_is_leap_month,
            )
        elif self.birth_is_leap_month and self.calendar_type != "lunar":
            raise ValueError("birth_date_invalid")
        return self


class ReportTaskResponse(BaseModel):
    task_id: str
    status: str = "processing"
    estimated_time: int = 5


class ReportTaskStatusResponse(BaseModel):
    task_id: str
    status: str  # processing/completed/failed
    report_id: Optional[int] = None
    report_data: Optional[Dict[str, Any]] = None
    progress: int = 0
    error: Optional[str] = None


class ReportListItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    energy_type: Optional[str] = None
    core_traits: Optional[str] = None
    summary: Optional[str] = None
    day_pillar: Optional[str] = None
    cover_description: Optional[str] = Field(None, description="Short introduction shown on the report cover.")

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    total: int
    items: List[ReportListItem]


class ReportResponse(BaseModel):
    id: int
    title: str
    basic_info: Dict[str, Any]
    energy_profile: Dict[str, Any]
    career_guidance: Dict[str, Any]
    relationship_pattern: Dict[str, Any]
    personal_growth: Dict[str, Any]
    summary: Optional[str]
    content_payload: Optional[Dict[str, Any]] = None
    ai_generated_content: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    input_snapshot: Optional[Dict[str, Any]] = None
    profile_version: Optional[int] = None
    context: Optional[ReportContext] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportPdfPreviewRequest(BaseModel):
    report: Dict[str, Any]


class LatestReportContextResponse(BaseModel):
    report_id: Optional[int] = None
    created_at: Optional[datetime] = None
    context: Optional[ReportContext] = None
