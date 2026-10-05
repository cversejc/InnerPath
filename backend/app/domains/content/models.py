from sqlalchemy import (
    Boolean,
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class CaseEvidenceItem(Base):
    __tablename__ = "case_evidence_items"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id", "evidence_key", name="uq_case_evidence_key"
        ),
        CheckConstraint(
            "source_type IN ('USER_PROVIDED', 'SYSTEM_CALCULATED', 'EXTERNAL_REFERENCE')",
            name="ck_case_evidence_source_type",
        ),
        CheckConstraint("status IN ('ACTIVE', 'RETRACTED')", name="ck_case_evidence_status"),
        Index("ix_case_evidence_case_status", "report_case_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_key = Column(String(240), nullable=False)
    source_type = Column(String(32), nullable=False)
    source_ref = Column(String(500), nullable=False)
    value_json = Column(JsonDocument, nullable=False)
    status = Column(String(16), nullable=False, default="ACTIVE", index=True)
    status_reason = Column(Text, nullable=True)
    source_skill_run_id = Column(
        Integer, ForeignKey("skill_runs.id", ondelete="RESTRICT"), nullable=True
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)


class FindingRevision(Base):
    __tablename__ = "finding_revisions"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id",
            "finding_key",
            "revision_no",
            name="uq_finding_revision_number",
        ),
        CheckConstraint("revision_no > 0", name="ck_finding_revision_positive"),
        CheckConstraint(
            "semantic_revision > 0 AND content_revision > 0",
            name="ck_finding_revision_counters_positive",
        ),
        CheckConstraint(
            "kind IN ('FINDING', 'SIGNAL')", name="ck_finding_revision_kind"
        ),
        CheckConstraint(
            "confidence IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_finding_revision_confidence",
        ),
        CheckConstraint(
            "importance IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_finding_revision_importance",
        ),
        CheckConstraint(
            "reportability IN ('INTERNAL_ONLY', 'OPTIONAL', 'RECOMMENDED', 'MUST_INCLUDE')",
            name="ck_finding_revision_reportability",
        ),
        CheckConstraint(
            "status IN ('PROPOSED', 'CONFIRMED', 'REJECTED', 'SUPERSEDED')",
            name="ck_finding_revision_status",
        ),
        CheckConstraint(
            "edit_kind IN ('SEMANTIC', 'STYLE')", name="ck_finding_edit_kind"
        ),
        Index(
            "uq_finding_revision_current",
            "report_case_id",
            "finding_key",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        Index("ix_finding_revision_case_status", "report_case_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False
    )
    finding_key = Column(String(200), nullable=False)
    revision_no = Column(Integer, nullable=False)
    semantic_revision = Column(Integer, nullable=False)
    content_revision = Column(Integer, nullable=False)
    kind = Column(String(16), nullable=False, default="FINDING")
    semantic_role = Column(String(48), nullable=False)
    claim = Column(Text, nullable=False)
    confidence = Column(String(12), nullable=False)
    importance = Column(String(12), nullable=False)
    reportability = Column(String(24), nullable=False)
    status = Column(String(16), nullable=False, default="PROPOSED")
    evidence_refs = Column(JsonDocument, nullable=False, default=list)
    relation_refs = Column(JsonDocument, nullable=False, default=list)
    structured_data_json = Column(JsonDocument, nullable=False, default=dict)
    edit_kind = Column(String(12), nullable=False, default="SEMANTIC")
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    owner_step_task_id = Column(
        Integer, ForeignKey("step_tasks.id", ondelete="SET NULL"), nullable=True
    )
    source_skill_run_id = Column(
        Integer, ForeignKey("skill_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)


class NarrativePlan(Base):
    __tablename__ = "narrative_plans"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id", "version_no", name="uq_narrative_plan_case_version"
        ),
        CheckConstraint("version_no > 0", name="ck_narrative_plan_version_positive"),
        CheckConstraint(
            "status IN ('PROPOSED', 'CONFIRMED', 'STALE', 'SUPERSEDED')",
            name="ck_narrative_plan_status",
        ),
        Index(
            "uq_narrative_plan_current",
            "report_case_id",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        Index("ix_narrative_plan_case_status", "report_case_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False
    )
    version_no = Column(Integer, nullable=False)
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    status = Column(String(16), nullable=False, default="PROPOSED", index=True)
    selected_skill_run_id = Column(
        Integer, ForeignKey("skill_runs.id", ondelete="RESTRICT"), nullable=False
    )
    selected_candidate_key = Column(String(100), nullable=False)
    plan_json = Column(JsonDocument, nullable=False)
    source_snapshot = Column(JsonDocument, nullable=False)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)


class ContentFragmentRevision(Base):
    __tablename__ = "content_fragment_revisions"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id",
            "fragment_key",
            "revision_no",
            name="uq_content_fragment_revision_number",
        ),
        CheckConstraint("revision_no > 0", name="ck_content_fragment_revision_positive"),
        CheckConstraint(
            "semantic_revision > 0 AND content_revision > 0",
            name="ck_content_fragment_revision_counters_positive",
        ),
        CheckConstraint(
            "fragment_type IN ('ANALYSIS', 'REPORT')",
            name="ck_content_fragment_type",
        ),
        CheckConstraint(
            "status IN ('PROPOSED', 'CONFIRMED', 'STALE')",
            name="ck_content_fragment_status",
        ),
        CheckConstraint(
            "edit_kind IN ('SEMANTIC', 'STYLE')", name="ck_content_fragment_edit_kind"
        ),
        Index(
            "uq_content_fragment_revision_current",
            "report_case_id",
            "fragment_key",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        Index(
            "ix_content_fragment_case_status",
            "report_case_id",
            "status",
        ),
        Index("ix_content_fragment_narrative_plan", "source_narrative_plan_id"),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False
    )
    fragment_key = Column(String(200), nullable=False)
    revision_no = Column(Integer, nullable=False)
    semantic_revision = Column(Integer, nullable=False)
    content_revision = Column(Integer, nullable=False)
    fragment_type = Column(String(16), nullable=False, default="ANALYSIS")
    title = Column(String(240), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="PROPOSED")
    source_snapshot = Column(JsonDocument, nullable=False, default=dict)
    edit_kind = Column(String(12), nullable=False, default="SEMANTIC")
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    owner_step_task_id = Column(
        Integer, ForeignKey("step_tasks.id", ondelete="SET NULL"), nullable=True
    )
    source_skill_run_id = Column(
        Integer, ForeignKey("skill_runs.id", ondelete="SET NULL"), nullable=True
    )
    source_narrative_plan_id = Column(
        Integer, ForeignKey("narrative_plans.id", ondelete="RESTRICT"), nullable=True
    )
    stale_reason = Column(Text, nullable=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)
