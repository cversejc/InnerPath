from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


EvidenceSourceType = Literal[
    "USER_PROVIDED", "SYSTEM_CALCULATED", "EXTERNAL_REFERENCE"
]
FindingStatus = Literal["PROPOSED", "CONFIRMED", "REJECTED"]
EditKind = Literal["SEMANTIC", "STYLE"]


class EvidenceCreate(BaseModel):
    evidence_key: str = Field(..., min_length=1, max_length=240)
    source_type: EvidenceSourceType
    source_ref: str = Field(..., min_length=1, max_length=500)
    value: Any


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    evidence_key: str
    source_type: EvidenceSourceType
    source_ref: str
    value_json: Any
    status: str
    status_reason: Optional[str] = None
    source_skill_run_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime


class FindingRevisionCreate(BaseModel):
    expected_revision_no: Optional[int] = Field(None, ge=1)
    claim: str = Field(..., min_length=1, max_length=5000)
    kind: Literal["FINDING", "SIGNAL"] = "FINDING"
    semantic_role: str = Field(..., min_length=1, max_length=48)
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    importance: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    reportability: Literal[
        "INTERNAL_ONLY", "OPTIONAL", "RECOMMENDED", "MUST_INCLUDE"
    ] = "OPTIONAL"
    status: FindingStatus = "PROPOSED"
    evidence_refs: list[str] = Field(default_factory=list)
    relation_refs: list[dict[str, str]] = Field(default_factory=list)
    structured_data: dict[str, Any] = Field(default_factory=dict)
    edit_kind: EditKind = "SEMANTIC"


class FindingRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    finding_key: str
    revision_no: int
    semantic_revision: int
    content_revision: int
    kind: str
    semantic_role: str
    claim: str
    confidence: str
    importance: str
    reportability: str
    status: str
    evidence_refs: list[str]
    relation_refs: list[dict[str, str]]
    structured_data_json: dict[str, Any]
    edit_kind: str
    is_current: bool
    owner_step_task_id: Optional[int] = None
    source_skill_run_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime


class ContentFragmentRevisionCreate(BaseModel):
    expected_revision_no: Optional[int] = Field(None, ge=1)
    fragment_type: Literal["ANALYSIS", "REPORT"] = "ANALYSIS"
    title: Optional[str] = Field(None, max_length=240)
    content: str = Field(..., min_length=1, max_length=30000)
    status: Literal["PROPOSED", "CONFIRMED"] = "PROPOSED"
    finding_refs: list[str] = Field(default_factory=list)
    fragment_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    edit_kind: EditKind = "SEMANTIC"
    owner_step_task_id: Optional[int] = Field(None, gt=0)
    source_skill_run_id: Optional[int] = Field(None, gt=0)
    source_narrative_plan_id: Optional[int] = Field(None, gt=0)
    framework_coverage: Optional[dict[str, Any]] = None
    structured_analysis: Optional[dict[str, Any]] = None
    requirement_coverage: Optional[list[dict[str, Any]]] = None


class ContentFragmentRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    fragment_key: str
    revision_no: int
    semantic_revision: int
    content_revision: int
    fragment_type: str
    title: Optional[str] = None
    content: str
    status: str
    source_snapshot: dict[str, Any]
    edit_kind: str
    is_current: bool
    owner_step_task_id: Optional[int] = None
    source_skill_run_id: Optional[int] = None
    source_narrative_plan_id: Optional[int] = None
    stale_reason: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime


class ReportCaseContentResponse(BaseModel):
    evidence: list[EvidenceResponse]
    findings: list[FindingRevisionResponse]
    fragments: list[ContentFragmentRevisionResponse]


class NarrativePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_case_id: int
    version_no: int
    is_current: bool
    status: str
    selected_skill_run_id: int
    selected_candidate_key: str
    plan_json: dict[str, Any]
    source_snapshot: dict[str, Any]
    created_by: Optional[int] = None
    confirmed_by: Optional[int] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None


class NarrativeStateResponse(BaseModel):
    current_plan: Optional[NarrativePlanResponse] = None
    candidate_runs: list[dict[str, Any]] = Field(default_factory=list)
    fragment_runs: list[dict[str, Any]] = Field(default_factory=list)


class NarrativeCandidatesCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)
    runtime_instruction: Optional[str] = Field(None, max_length=4000)


class NarrativePlanConfirm(BaseModel):
    skill_run_id: int
    candidate_key: str = Field(..., min_length=1, max_length=100)
    overrides: dict[str, Any] = Field(default_factory=dict)


class AnalysisCandidateApplyInput(BaseModel):
    expected_revision_no: Optional[int] = Field(None, ge=1)


class ReportFragmentGenerate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)
    fragment_key: str = Field(..., min_length=1, max_length=200)
    title: Optional[str] = Field(None, max_length=240)
    runtime_instruction: Optional[str] = Field(None, max_length=4000)


class ReportGenerationCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)
