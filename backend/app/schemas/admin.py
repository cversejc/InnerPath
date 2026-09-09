from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.booking import BookingResponse
from app.schemas.report import ReportListItem, ReportResponse
from app.schemas.user import UserResponse


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(user|consultant|admin)$")


class AdminPasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    birth_month: Optional[int] = Field(None, ge=1, le=12)
    birth_day: Optional[int] = Field(None, ge=1, le=31)
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None


class AdminUserListItem(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    user_type: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    report_count: int = 0
    booking_count: int = 0
    calendar_count: int = 0

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    total: int
    page: int = 1
    size: int = 20
    items: list[AdminUserListItem]


class AdminUserSummary(BaseModel):
    report_count: int = 0
    booking_count: int = 0
    calendar_count: int = 0
    published_calendar_count: int = 0
    decision_log_count: int = 0
    course_count: int = 0
    average_course_progress: float = 0


class AdminUserSummaryResponse(BaseModel):
    user: UserResponse
    summary: AdminUserSummary


class AdminBookingResponse(BookingResponse):
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    cancellation_reason: Optional[str] = None


class AdminBookingListResponse(BaseModel):
    total: int
    page: int = 1
    size: int = 20
    items: list[AdminBookingResponse]


class AdminDecisionLogResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    log_date: date
    kind: str
    status: str
    content: str
    note: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminDecisionLogListResponse(BaseModel):
    total: int
    page: int = 1
    size: int = 50
    items: list[AdminDecisionLogResponse]


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    target_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    target_user_name: Optional[str] = None
    request_id: Optional[str] = None
    user_agent: Optional[str] = None
    details_json: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    total: int
    page: int = 1
    size: int = 50
    items: list[AuditLogResponse]


class AdminReportListItem(ReportListItem):
    user_id: int
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    status: str
    is_deleted: bool = False
    ai_model: Optional[str] = None
    generation_time_ms: Optional[int] = None
    task_id: Optional[str] = None
    task_status: Optional[str] = None
    task_progress: Optional[int] = None
    task_error: Optional[str] = None


class AdminReportListResponse(BaseModel):
    total: int
    page: int = 1
    size: int = 20
    items: list[AdminReportListItem]


class AdminReportResponse(ReportResponse):
    user_id: int
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    status: str
    is_deleted: bool = False
    ai_model: Optional[str] = None
    generation_time_ms: Optional[int] = None


class AdminReportTaskResponse(BaseModel):
    task_id: str
    user_id: int
    user_name: Optional[str] = None
    status: str
    progress: int
    report_id: Optional[int] = None
    error: Optional[str] = None
    retry_count: int = 0
    retry_of_task_id: Optional[str] = None
    has_input_snapshot: bool = False
    has_retry: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminReportTaskListResponse(BaseModel):
    total: int
    page: int = 1
    size: int = 20
    items: list[AdminReportTaskResponse]


class DashboardMetricResponse(BaseModel):
    user_total: int = 0
    active_users: int = 0
    new_users: int = 0
    report_total: int = 0
    report_success_rate: float = 0
    report_processing: int = 0
    report_failed: int = 0
    booking_pending: int = 0
    booking_confirmed: int = 0
    booking_completed: int = 0
    published_calendars: int = 0
    decision_logs: int = 0
    active_learners: int = 0


class DashboardTrendPoint(BaseModel):
    date: date
    new_users: int = 0
    reports: int = 0
    bookings: int = 0
    decision_logs: int = 0


class DashboardDistributionItem(BaseModel):
    key: str
    label: str
    value: int


class DashboardDistributionResponse(BaseModel):
    users_by_role: list[DashboardDistributionItem] = Field(default_factory=list)
    bookings_by_status: list[DashboardDistributionItem] = Field(default_factory=list)
    reports_by_status: list[DashboardDistributionItem] = Field(default_factory=list)
    calendars_by_status: list[DashboardDistributionItem] = Field(default_factory=list)


class DashboardCourseStat(BaseModel):
    course_id: int
    title: str
    total_lessons: int
    enrolled_count: int = 0
    active_count: int = 0
    completed_count: int = 0
    completion_rate: float = 0
    average_progress: float = 0


class DashboardAlert(BaseModel):
    key: str
    level: str
    label: str
    count: int
    route: Optional[str] = None


class DashboardOverviewResponse(BaseModel):
    range_preset: str
    start_date: date
    end_date: date
    timezone: str
    metrics: DashboardMetricResponse
    trends: list[DashboardTrendPoint]
    distributions: DashboardDistributionResponse
    course_stats: list[DashboardCourseStat] = Field(default_factory=list)
    alerts: list[DashboardAlert]
    recent_activity: list[AuditLogResponse]


class AdminProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True
