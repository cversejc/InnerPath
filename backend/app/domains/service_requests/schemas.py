from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.domains.users.lunar_calendar import solar_date_for_birth


ServiceType = Literal["report", "calendar"]


class ServiceProfileSnapshot(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: str = Field(..., pattern="^(male|female)$")
    birth_year: int = Field(..., ge=1900, le=2026)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_is_leap_month: bool = False
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    calendar_type: str = Field("solar", pattern="^(solar|lunar)$")
    time_accuracy: str = Field("unknown", pattern="^(unknown|approximate|exact)$")

    @model_validator(mode="after")
    def validate_birth_date(self):
        solar_date_for_birth(
            self.birth_year,
            self.birth_month,
            self.birth_day,
            calendar_type=self.calendar_type,
            is_leap_month=self.birth_is_leap_month,
        )
        return self


class ServiceRequestCreate(BaseModel):
    service_type: ServiceType
    profile: ServiceProfileSnapshot
    profile_version: Optional[int] = Field(None, ge=1)
    context: Optional[Dict[str, Any]] = None
    selected_topics: List[str] = Field(default_factory=list, max_length=12)
    additional_info: Optional[str] = Field(None, max_length=4000)
    calendar_goal: Optional[str] = Field(None, max_length=500)
    start_date: Optional[date] = None
    idempotency_key: Optional[str] = Field(None, min_length=8, max_length=128)


class ServiceRequestUpdate(BaseModel):
    profile: Optional[ServiceProfileSnapshot] = None
    selected_topics: Optional[List[str]] = Field(None, max_length=12)
    additional_info: Optional[str] = Field(None, max_length=4000)
    calendar_goal: Optional[str] = Field(None, max_length=500)
    start_date: Optional[date] = None


class ServiceRequestResponse(BaseModel):
    id: int
    service_type: ServiceType
    status: str
    request_payload: Dict[str, Any]
    result_type: Optional[str] = None
    result_id: Optional[int] = None
    assigned_consultant_id: Optional[int] = None
    assigned_mingli_consultant_id: Optional[int] = None
    assigned_psychology_consultant_id: Optional[int] = None
    needs_info_reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    last_error: Optional[str] = None
    assigned_consultant_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    ai_started_at: Optional[datetime] = None
    ai_completed_at: Optional[datetime] = None
    reviewing_at: Optional[datetime] = None
    needs_info_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    report_case_id: Optional[int] = None
    report_case_status: Optional[str] = None
    current_step_key: Optional[str] = None


class ServiceRequestListResponse(BaseModel):
    total: int
    items: List[ServiceRequestResponse]


class StaffServiceRequestListItem(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    service_type: ServiceType
    status: str
    request_preview: Dict[str, Any] = Field(default_factory=dict)
    assigned_consultant_id: Optional[int] = None
    assigned_mingli_consultant_id: Optional[int] = None
    assigned_psychology_consultant_id: Optional[int] = None
    assigned_consultant_name: Optional[str] = None
    needs_info_reason: Optional[str] = None
    last_error: Optional[str] = None
    report_case_id: Optional[int] = None
    report_case_status: Optional[str] = None
    current_step_key: Optional[str] = None
    current_step_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StaffServiceRequestListResponse(BaseModel):
    total: int
    items: List[StaffServiceRequestListItem]


class ServiceRequestTaskResponse(BaseModel):
    task_id: str
    request_id: int
    service_type: ServiceType
    status: str
    progress: int = 0
    error: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceRequestDraftUpdate(BaseModel):
    payload: Dict[str, Any]
    expected_version: Optional[int] = Field(None, ge=1)


class ServiceRequestDraftResponse(BaseModel):
    request_id: int
    ai_payload: Dict[str, Any]
    editable_payload: Dict[str, Any]
    ai_version: int
    content_version: int
    updated_at: datetime


class ServiceRequestWorkspaceResponse(BaseModel):
    request: ServiceRequestResponse
    user: Dict[str, Any]
    draft: Optional[ServiceRequestDraftResponse] = None
    task: Optional[ServiceRequestTaskResponse] = None


class ServiceRequestInfoInput(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class ServiceRequestAssignmentUpdate(BaseModel):
    consultant_id: Optional[int] = None
    consultant_type: Optional[Literal["mingli", "psychology"]] = None


class ServiceRequestRegenerateInput(BaseModel):
    confirm_overwrite: bool = False


class ServiceRequestListQuery(BaseModel):
    status: Optional[str] = None
    service_type: Optional[ServiceType] = None
