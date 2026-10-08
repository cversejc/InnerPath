from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import ConfigDict, Field
from app.core.schemas import APIModel as BaseModel


class QAIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    source_type: str
    source_ref_id: Optional[int] = None
    issue_type: str
    severity: str
    status: str
    target_fragment_key: Optional[str] = None
    target_fragment_revision_id: Optional[int] = None
    message: str
    evidence_json: dict[str, Any]
    suggestion: Optional[str] = None
    resolution: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class QAIssueResolution(BaseModel):
    status: Literal["RESOLVED", "ACCEPTED", "DISMISSED"]
    resolution: str = Field(..., min_length=3, max_length=2000)


class QAIssueGroupResolution(BaseModel):
    """同类型检查问题整体处理：一次填写依据，每条问题仍单独留痕。"""

    issue_ids: list[int] = Field(min_length=1, max_length=200)
    status: Literal["RESOLVED", "ACCEPTED", "DISMISSED"]
    resolution: str = Field(..., min_length=3, max_length=2000)


class QualityRunRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)
    runtime_instruction: Optional[str] = Field(None, max_length=4000)
    source_run_id: Optional[int] = Field(None, ge=1)


class FinalGateApproval(BaseModel):
    attested: bool
    note: Optional[str] = Field(None, max_length=2000)


class ReportQualityResponse(BaseModel):
    report_case_id: int
    latest_validator_run: Optional[dict[str, Any]] = None
    quality_status: str
    issues: list[QAIssueResponse]
    issue_groups: list[dict[str, Any]] = Field(default_factory=list)
    can_approve: bool
    blocking_count: int
    open_count: int
    qa_fingerprint_current: Optional[str] = None


class AdminQAIssueItem(BaseModel):
    id: int
    is_current: bool
    report_case_id: int
    report_case_status: str
    user_id: int
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    service_request_id: Optional[int] = None
    source_type: str
    source_ref_id: Optional[int] = None
    issue_type: str
    severity: str
    status: str
    target_fragment_key: Optional[str] = None
    message: str
    suggestion: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class AdminQAIssueListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[AdminQAIssueItem]
