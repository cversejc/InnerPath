from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
    text,
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


class SkillExample(Base):
    __tablename__ = "skill_examples"
    __table_args__ = (
        UniqueConstraint(
            "example_key", "version_no", name="uq_skill_example_key_version"
        ),
        CheckConstraint("version_no > 0", name="ck_skill_example_version_positive"),
        CheckConstraint(
            "status IN ('CANDIDATE', 'PUBLISHED', 'RETIRED')",
            name="ck_skill_example_status",
        ),
        CheckConstraint(
            "example_type IN ('POSITIVE', 'CONTRASTIVE', 'MISSED_INSIGHT')",
            name="ck_skill_example_type",
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)",
            name="ck_skill_example_quality_score",
        ),
        Index(
            "uq_skill_example_published_key",
            "example_key",
            unique=True,
            postgresql_where=text("status = 'PUBLISHED'"),
            sqlite_where=text("status = 'PUBLISHED'"),
        ),
        Index(
            "ix_skill_examples_retrieval",
            "skill_key",
            "status",
            "target_fragment_key",
        ),
    )

    id = Column(Integer, primary_key=True)
    skill_key = Column(String(100), nullable=False, index=True)
    target_fragment_key = Column(String(200), nullable=True)
    example_key = Column(String(64), nullable=False)
    version_no = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="CANDIDATE", index=True)
    example_type = Column(String(24), nullable=False)
    scenario_tags = Column(JsonDocument, nullable=False, default=list)
    applicability_json = Column(JsonDocument, nullable=False, default=dict)
    input_context = Column(JsonDocument, nullable=False, default=dict)
    expected_output = Column(JsonDocument, nullable=False, default=dict)
    teaching_points = Column(JsonDocument, nullable=False, default=list)
    anti_patterns = Column(JsonDocument, nullable=False, default=list)
    quality_score = Column(Float, nullable=True)
    source_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="SET NULL"), nullable=True
    )
    source_skill_run_id = Column(
        Integer, ForeignKey("skill_runs.id", ondelete="SET NULL"), nullable=True
    )
    deidentified = Column(Boolean, nullable=False, default=False)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)
    published_at = Column(DateTime, nullable=True)


@event.listens_for(SkillExample, "before_update")
def _prevent_published_skill_example_mutation(_mapper, _connection, target) -> None:
    state = inspect(target)
    changed = {attribute.key for attribute in state.attrs if attribute.history.has_changes()}
    status_history = state.attrs.status.history
    if (
        changed == {"status"}
        and status_history.deleted == ["PUBLISHED"]
        and status_history.added == ["RETIRED"]
    ):
        return
    if status_history.deleted == ["PUBLISHED"]:
        raise ValueError("skill_example_immutable")
    if target.status == "PUBLISHED":
        allowed_publish_fields = {"status", "reviewed_by", "published_at"}
        if (
            status_history.deleted == ["CANDIDATE"]
            and status_history.added == ["PUBLISHED"]
            and changed.issubset(allowed_publish_fields)
        ):
            return
        raise ValueError("skill_example_immutable")


@event.listens_for(SkillExample, "before_delete")
def _prevent_published_skill_example_delete(_mapper, _connection, target) -> None:
    if target.status == "PUBLISHED":
        raise ValueError("skill_example_immutable")
