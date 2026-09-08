from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ReportCreate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: str = Field(..., pattern="^(male|female)$")
    birth_year: int = Field(..., ge=1900, le=2026)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(None, ge=0, le=59)
    birth_place: Optional[str] = Field(None, max_length=100)
    calendar_type: str = Field("solar", pattern="^(solar|lunar)$")
    selected_topics: List[str] = Field(default_factory=list)
    additional_info: Optional[str] = None


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
    ai_generated_content: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
