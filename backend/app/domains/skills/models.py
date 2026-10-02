from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class AISkillVersion(Base):
    __tablename__ = "ai_skill_versions"
    __table_args__ = (
        UniqueConstraint(
            "skill_key", "version", name="uq_ai_skill_version_key_version"
        ),
        CheckConstraint("version > 0", name="ck_ai_skill_version_positive"),
        CheckConstraint(
            "status IN ('DRAFT', 'EVALUATION', 'PUBLISHED', 'RETIRED')",
            name="ck_ai_skill_version_status",
        ),
        CheckConstraint(
            "category IN ('ANALYSIS', 'ACTION', 'AUTHORING', 'VALIDATOR')",
            name="ck_ai_skill_version_category",
        ),
    )

    id = Column(Integer, primary_key=True)
    skill_key = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(24), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="DRAFT", index=True)
    specification_json = Column(JsonDocument, nullable=False)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)
    published_at = Column(DateTime, nullable=True)


class SkillRun(Base):
    __tablename__ = "skill_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_skill_run_idempotency_key"),
        CheckConstraint(
            "run_type IN ('INITIAL', 'REGENERATE', 'REWRITE', 'VALIDATE', 'EVALUATION')",
            name="ck_skill_run_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_skill_run_status",
        ),
        Index("ix_skill_runs_case_status", "report_case_id", "status"),
        Index("ix_skill_runs_skill_version_id", "skill_version_id"),
        Index("ix_skill_runs_version_created", "skill_version_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    skill_version_id = Column(
        Integer, ForeignKey("ai_skill_versions.id", ondelete="RESTRICT"), nullable=False
    )
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=True
    )
    workflow_instance_id = Column(
        Integer, ForeignKey("workflow_instances.id", ondelete="RESTRICT"), nullable=True
    )
    step_task_id = Column(
        Integer, ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=True
    )
    target_type = Column(String(32), nullable=False)
    target_key = Column(String(128), nullable=True)
    run_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    idempotency_key = Column(String(200), nullable=False)
    runtime_instruction = Column(Text, nullable=True)
    input_snapshot = Column(JsonDocument, nullable=False)
    context_snapshot = Column(JsonDocument, nullable=False)
    output_raw = Column(Text, nullable=True)
    output_parsed = Column(JsonDocument, nullable=True)
    selected_examples = Column(JsonDocument, nullable=False, default=list)
    selected_knowledge = Column(JsonDocument, nullable=False, default=list)
    model_trace = Column(JsonDocument, nullable=False, default=dict)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
