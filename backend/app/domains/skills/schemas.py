from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import ConfigDict, Field, field_validator
from app.core.schemas import APIModel as BaseModel


class SkillVersionCreate(BaseModel):
    skill_key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(ANALYSIS|ACTION|AUTHORING|VALIDATOR)$")
    specification_json: dict[str, Any]


class SkillVersionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(ANALYSIS|ACTION|AUTHORING|VALIDATOR)$")
    specification_json: dict[str, Any]


class SkillReasoningGuidanceUpdate(BaseModel):
    objective: str = Field(..., max_length=1200)
    methodology: list[str] = Field(..., min_length=1, max_length=40)

    @field_validator("objective")
    @classmethod
    def normalize_objective(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("skill_instruction_objective_required")
        return value

    @field_validator("methodology")
    @classmethod
    def normalize_methodology(cls, values: list[str]) -> list[str]:
        methodology = [value.strip() for value in values if value and value.strip()]
        if not methodology:
            raise ValueError("skill_instruction_methodology_required")
        if any(len(value) > 1000 for value in methodology):
            raise ValueError("skill_instruction_methodology_item_too_long")
        return methodology


class SkillReasoningGuidance(BaseModel):
    objective: str
    methodology: list[str]


class SkillVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_key: str
    name: str
    category: str
    version: int
    status: str
    specification_json: Optional[dict[str, Any]] = None
    reasoning_guidance: Optional[SkillReasoningGuidance] = None
    created_by: Optional[int] = None
    published_by: Optional[int] = None
    created_at: datetime
    published_at: Optional[datetime] = None


class SkillRunCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)
    input_data: dict[str, Any]
    runtime_instruction: Optional[str] = Field(None, max_length=4000)


class StepSkillRunCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=200)
    runtime_instruction: Optional[str] = Field(None, max_length=4000)


class ReportAnalysisDraftCreate(StepSkillRunCreate):
    source_run_id: Optional[int] = Field(None, ge=1)


class SkillRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    skill_version_id: int
    report_case_id: Optional[int] = None
    workflow_instance_id: Optional[int] = None
    step_task_id: Optional[int] = None
    target_type: str
    target_key: Optional[str] = None
    run_type: str
    status: str
    input_snapshot: dict[str, Any]
    context_snapshot: dict[str, Any]
    runtime_instruction: Optional[str] = None
    output_raw: Optional[str] = None
    output_parsed: Optional[dict[str, Any]] = None
    selected_examples: list[Any]
    selected_knowledge: list[Any]
    model_trace: dict[str, Any]
    error: Optional[str] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ConsultantSkillRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    skill_version_id: int
    report_case_id: Optional[int] = None
    step_task_id: Optional[int] = None
    target_type: str
    target_key: Optional[str] = None
    run_type: str
    status: str
    context_snapshot: dict[str, Any]
    runtime_instruction: Optional[str] = None
    selected_examples: list[Any]
    selected_knowledge: list[Any]
    output_parsed: Optional[dict[str, Any]] = None
    model_trace: dict[str, Any]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SkillExampleRecommendation(BaseModel):
    skill_run_id: int = Field(..., ge=1)
    example_type: Literal["POSITIVE", "CONTRASTIVE", "MISSED_INSIGHT"]
    scenario_tags: list[str] = Field(default_factory=list, max_length=12)
    teaching_points: list[str] = Field(default_factory=list, max_length=12)
    expected_output: Optional[dict[str, Any]] = None


class SkillExampleRedaction(BaseModel):
    target_fragment_key: Optional[str] = Field(None, max_length=200)
    scenario_tags: list[str] = Field(default_factory=list, max_length=12)
    applicability_json: dict[str, Any] = Field(default_factory=dict)
    input_context: dict[str, Any]
    expected_output: dict[str, Any]
    teaching_points: list[str] = Field(default_factory=list, max_length=12)
    anti_patterns: list[str] = Field(default_factory=list, max_length=12)
    quality_score: float = Field(..., ge=0, le=1)
    confirmed_deidentified: bool


class SkillExampleAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_key: str
    target_fragment_key: Optional[str] = None
    example_key: str
    version_no: int
    status: str
    example_type: str
    scenario_tags: list[str]
    applicability_json: dict[str, Any]
    input_context: dict[str, Any]
    expected_output: dict[str, Any]
    teaching_points: list[str]
    anti_patterns: list[str]
    quality_score: Optional[float] = None
    source_case_id: Optional[int] = None
    source_skill_run_id: Optional[int] = None
    deidentified: bool
    created_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    created_at: datetime
    published_at: Optional[datetime] = None


class SkillExamplePublicResponse(BaseModel):
    id: int
    skill_key: str
    target_fragment_key: Optional[str] = None
    example_key: str
    version_no: int
    status: str
    example_type: str
    scenario_tags: list[str]
    applicability_json: dict[str, Any]
    input_context: dict[str, Any]
    expected_output: dict[str, Any]
    teaching_points: list[str]
    anti_patterns: list[str]
    quality_score: float


class RegressionCaseResponse(BaseModel):
    case_key: str
    title: str
    description: str


class SkillEvaluationCreate(BaseModel):
    case_keys: list[str] = Field(default_factory=list, max_length=50)


class SkillEvaluationBatchResponse(BaseModel):
    batch_id: str
    dataset_version: str
    total: int
    completed: int
    failed: int
    passed: int
    pass_rate: Optional[float] = None
    runs: list[dict[str, Any]]


class SkillEvaluationCaseResponse(RegressionCaseResponse):
    skill_key: str
