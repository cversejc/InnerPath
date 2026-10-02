from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class StepReturnInput(BaseModel):
    target_step_key: str = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=1, max_length=1000)


class StepAssignmentInput(BaseModel):
    assignee_id: Optional[int] = Field(None, gt=0)
