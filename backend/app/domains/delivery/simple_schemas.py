"""Request and response models for the simplified report workflow."""

from datetime import datetime
from typing import Optional

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
