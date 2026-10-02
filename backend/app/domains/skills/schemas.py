from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillVersionCreate(BaseModel):
    skill_key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(ANALYSIS|ACTION|AUTHORING|VALIDATOR)$")
    specification_json: dict[str, Any]


class SkillVersionUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(ANALYSIS|ACTION|AUTHORING|VALIDATOR)$")
    specification_json: dict[str, Any]


class SkillVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_key: str
    name: str
    category: str
    version: int
    status: str
    specification_json: dict[str, Any]
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
    output_parsed: Optional[dict[str, Any]] = None
    model_trace: dict[str, Any]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
