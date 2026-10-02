from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class QualityRunRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)


class FinalGateApproval(BaseModel):
    attested: bool
    note: Optional[str] = Field(None, max_length=2000)


class ReportQualityResponse(BaseModel):
    report_case_id: int
    latest_validator_run: Optional[dict[str, Any]] = None
    quality_status: str
    issues: list[QAIssueResponse]
    can_approve: bool
    blocking_count: int
    open_count: int
    qa_fingerprint_current: Optional[str] = None
