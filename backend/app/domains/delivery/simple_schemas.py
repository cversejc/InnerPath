"""Request and response models for the simplified report workflow."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import ConfigDict, Field

from app.core.schemas import APIModel as BaseModel


class SimpleStepCompleteInput(BaseModel):
    """Client payload for one simplified node.

    Only the report text is client supplied.  Round numbers, version numbers
    and the final flag are derived on the server from the step task, so extra
    fields are rejected instead of silently ignored.
    """

    model_config = ConfigDict(extra="forbid")

    report_text: str = Field(..., strict=True, min_length=1, max_length=200_000)
    review_note: Optional[str] = Field(None, max_length=4000)
    final_gate_confirmed: bool = Field(False, strict=True)


class SimpleReportVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    step_task_id: int
    round_no: int
    version_no: int
    version_label: str
    source_step_key: str
    report_text: str
    review_note: Optional[str] = None
    is_final: bool
    created_by: Optional[int] = None
    created_at: datetime


class SimpleReportVersionListResponse(BaseModel):
    total: int
    items: list[SimpleReportVersionResponse]


class SimpleStepCompletionResponse(BaseModel):
    version: SimpleReportVersionResponse
    delivered: bool
    report_id: Optional[int] = None


SimpleReviewMode = Literal["OWNER", "ADMIN", "DELEGATED"]


class SimpleStepActionInput(BaseModel):
    """Common idempotency and review-identity fields for AI step actions."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(..., min_length=1, max_length=200)
    review_mode: Optional[SimpleReviewMode] = None
    on_behalf_of_user_id: Optional[int] = Field(None, gt=0)


class SimpleGenerateInput(SimpleStepActionInput):
    """Start the first generation for an AI-assisted Simple step."""


class SimpleReviseInput(SimpleStepActionInput):
    """Request an AI revision against one exact immutable revision."""

    base_revision_id: int = Field(..., gt=0)
    feedback_text: str = Field(..., min_length=1, max_length=20_000)


class SimpleRegenerateInput(SimpleStepActionInput):
    """Request a full AI regeneration against one immutable revision."""

    base_revision_id: int = Field(..., gt=0)
    feedback_text: Optional[str] = Field(None, max_length=20_000)


class SimpleManualEditInput(SimpleStepActionInput):
    """Save a manual revision against the current immutable revision."""

    base_revision_id: int = Field(..., gt=0)
    content: str = Field("", max_length=200_000)
    structured_content: Optional[dict[str, Any]] = None


class SimpleApproveInput(SimpleStepActionInput):
    """Approve one exact immutable revision and complete the step."""

    base_revision_id: int = Field(..., gt=0)
    final_gate_confirmed: bool = False
    review_note: Optional[str] = Field(None, max_length=4000)


class SimpleReopenInput(SimpleStepActionInput):
    """Reopen a completed AI-assisted Simple step."""

    reason: Optional[str] = Field(None, max_length=4000)


class SimpleFinalizeInput(SimpleStepActionInput):
    """Placeholder contract for the phase-three final delivery command."""

    final_gate_confirmed: bool = False


class SimpleStepRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_no: int
    revision_type: str
    parent_revision_id: Optional[int] = None
    content: str
    structured_content: Optional[dict[str, Any]] = None
    source_revision_refs: dict[str, Any] = Field(default_factory=dict)
    skill_run_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime


class SimpleStepRevisionListResponse(BaseModel):
    total: int
    items: list[SimpleStepRevisionResponse]


class SimpleStepExecutionResponse(BaseModel):
    id: int
    report_case_id: int
    step_task_id: int
    step_key: str
    execution_status: str
    dependency_status: str
    activation_no: int
    current_revision_id: Optional[int] = None
    confirmed_revision_id: Optional[int] = None
    active_skill_run_id: Optional[int] = None
    input_fingerprint: Optional[str] = None
    stale_reason: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SimpleStepStateResponse(BaseModel):
    step_key: str
    step_name: str
    task_status: str
    last_error: Optional[str] = None
    execution: SimpleStepExecutionResponse
    current_revision: Optional[SimpleStepRevisionResponse] = None
    confirmed_revision: Optional[SimpleStepRevisionResponse] = None


class SimpleQualityResponse(BaseModel):
    step_key: str
    execution_status: str
    dependency_status: str
    revision_id: Optional[int] = None
    quality: Any = None
    hard_blocks: list[Any] = Field(default_factory=list)
    validator_findings: Any = None


class SimpleFinalizeResponse(BaseModel):
    report_case_id: int
    delivered: bool
    report_id: Optional[int] = None
    simple_version_id: Optional[int] = None
