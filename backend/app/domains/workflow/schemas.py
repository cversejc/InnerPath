from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field
from app.core.schemas import APIModel as BaseModel


class WorkflowVersionCreate(BaseModel):
    workflow_key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    definition_json: dict[str, Any]


class WorkflowVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_key: str
    name: str
    version: int
    status: str
    definition_json: dict[str, Any]
    created_by: Optional[int] = None
    published_by: Optional[int] = None
    created_at: datetime
    published_at: Optional[datetime] = None


class StepTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_key: str
    sequence_no: int
    executor: str
    status: str
    required_capability: Optional[str] = None
    assignee_id: Optional[int] = None
    activation_no: int
    config_snapshot: dict[str, Any]
    result_json: Optional[dict[str, Any]] = None
    activated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_version_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: list[StepTaskResponse]


class ReportCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    service_request_id: Optional[int] = None
    status: str
    application_snapshot: dict[str, Any]
    application_submitted_at: datetime
    workflow_instance: Optional[WorkflowInstanceResponse] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class ReportCaseListResponse(BaseModel):
    total: int
    items: list[ReportCaseResponse]


class StepCompleteInput(BaseModel):
    result_json: Optional[dict[str, Any]] = None


class StepCompletionGateResponse(BaseModel):
    step_key: str
    can_complete: bool
    confirmed_finding_count: int
    confirmed_fragment_count: int
    pending_finding_count: int
    pending_fragment_count: int
    stale_fragment_count: int
    blockers: list[str]


class StepReturnInput(BaseModel):
    target_step_key: str = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=1, max_length=1000)


class ReportCaseSupplementInput(BaseModel):
    response_key: str = Field(..., min_length=8, max_length=128)
    answer: str = Field(..., min_length=1, max_length=4000)


class ReportCaseSupplementResponse(BaseModel):
    report_case_id: int
    service_request_id: int
    evidence_key: str
    step_key: str
    status: str


class StepAssignmentInput(BaseModel):
    assignee_id: Optional[int] = Field(None, gt=0)
