from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


FeedbackType = Literal["PRAISE", "SUGGESTION", "COMPLAINT"]
FeedbackStatus = Literal["NEW", "IN_PROGRESS", "RESOLVED"]


class ServiceFeedbackCreate(BaseModel):
    service_request_id: Optional[int] = Field(None, ge=1)
    calendar_request_id: Optional[int] = Field(None, ge=1)
    feedback_type: FeedbackType
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: str = Field(..., min_length=5, max_length=2000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("feedback_comment_too_short")
        return normalized


class MyServiceFeedbackItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_request_id: Optional[int] = None
    calendar_request_id: Optional[int] = None
    feedback_type: FeedbackType
    rating: Optional[int] = None
    comment: str
    status: FeedbackStatus
    resolution: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MyServiceFeedbackListResponse(BaseModel):
    items: list[MyServiceFeedbackItem]


class AdminServiceFeedbackItem(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    service_type: Literal["report", "calendar"]
    service_request_id: Optional[int] = None
    calendar_request_id: Optional[int] = None
    service_result_id: Optional[int] = None
    source_status: str
    feedback_type: FeedbackType
    rating: Optional[int] = None
    comment: str
    status: FeedbackStatus
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AdminServiceFeedbackListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[AdminServiceFeedbackItem]


class AdminServiceQualityMetrics(BaseModel):
    feedback_count: int = 0
    rated_count: int = 0
    average_rating: Optional[float] = None
    complaint_count: int = 0
    resolved_count: int = 0
    resolution_rate_percent: Optional[float] = None
    resolution_p50_hours: Optional[float] = None
    resolution_p90_hours: Optional[float] = None


class AdminServiceQualityGroup(AdminServiceQualityMetrics):
    key: str
    label: str


class AdminServiceQualityConsultantGroup(BaseModel):
    consultant_id: int
    consultant_name: str
    feedback_count: int = 0
    rated_count: int = 0
    average_rating: Optional[float] = None
    complaint_count: int = 0


class AdminServiceQualityTrendPoint(BaseModel):
    week_start: date
    feedback_count: int = 0
    rated_count: int = 0
    average_rating: Optional[float] = None
    complaint_count: int = 0


class AdminServiceQualitySummary(BaseModel):
    period_days: int
    range_start: date
    range_end: date
    totals: AdminServiceQualityMetrics
    by_service: list[AdminServiceQualityGroup] = Field(default_factory=list)
    by_specialty: list[AdminServiceQualityGroup] = Field(default_factory=list)
    by_consultant: list[AdminServiceQualityConsultantGroup] = Field(default_factory=list)
    weekly_trend: list[AdminServiceQualityTrendPoint] = Field(default_factory=list)


class AdminServiceFeedbackUpdate(BaseModel):
    status: FeedbackStatus
    assigned_to: Optional[int] = Field(None, ge=1)
    resolution: Optional[str] = Field(None, max_length=2000)

    @field_validator("resolution")
    @classmethod
    def normalize_resolution(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class AdminServiceFeedbackStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: FeedbackStatus
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    updated_at: datetime
