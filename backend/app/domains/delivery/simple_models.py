"""Persistence models for the simplified report workflow.

``SimpleReportVersion`` is the immutable output contract of the legacy manual
protocol.  The AI-assisted protocol uses one execution row per business step
plus an append-only revision history and immutable review decisions.  Its
generation runs intentionally reuse ``SkillRun`` instead of introducing a
second task-run table.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class SimpleReportVersion(Base):
    __tablename__ = "simple_report_versions"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id", "version_no", name="uq_simple_report_version_case_version"
        ),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    step_task_id = Column(
        Integer, ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    round_no = Column(Integer, nullable=False)
    version_no = Column(Integer, nullable=False)
    version_label = Column(String(20), nullable=False)
    source_step_key = Column(String(100), nullable=False)
    report_text = Column(Text, nullable=False)
    review_note = Column(Text, nullable=True)
    is_final = Column(Boolean, nullable=False, default=False)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)


@event.listens_for(SimpleReportVersion, "before_update")
@event.listens_for(SimpleReportVersion, "before_delete")
def _reject_simple_report_version_mutation(_mapper, _connection, _target) -> None:
    raise ValueError("simple_report_version_immutable")


class SimpleStepExecution(Base):
    """Current internal state for one AI-assisted Simple business step."""

    __tablename__ = "simple_step_executions"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id",
            "step_key",
            name="uq_simple_step_execution_case_step",
        ),
        CheckConstraint(
            "execution_status IN "
            "('READY', 'GENERATING', 'IN_REVIEW', 'REVISING', 'FAILED', 'COMPLETED')",
            name="ck_simple_step_execution_status",
        ),
        CheckConstraint(
            "dependency_status IN ('CURRENT', 'STALE')",
            name="ck_simple_step_execution_dependency_status",
        ),
        CheckConstraint(
            "activation_no >= 1",
            name="ck_simple_step_execution_activation_positive",
        ),
        Index(
            "ix_simple_step_executions_case_status",
            "report_case_id",
            "execution_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer,
        ForeignKey("report_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    step_task_id = Column(
        Integer,
        ForeignKey("step_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_key = Column(String(100), nullable=False)
    execution_status = Column(
        String(24), nullable=False, default="READY", index=True
    )
    dependency_status = Column(
        String(16), nullable=False, default="CURRENT", index=True
    )
    activation_no = Column(Integer, nullable=False)
    # These references are application-managed to avoid a circular table
    # dependency between executions and revisions.  Both IDs always point at
    # revisions in the same execution; the service layer enforces that rule.
    current_revision_id = Column(Integer, nullable=True)
    confirmed_revision_id = Column(Integer, nullable=True)
    active_skill_run_id = Column(
        Integer,
        ForeignKey("skill_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    input_snapshot = Column(JsonDocument, nullable=False, default=dict)
    input_fingerprint = Column(String(64), nullable=True)
    stale_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class SimpleStepRevision(Base):
    """An immutable content revision produced for one Simple step."""

    __tablename__ = "simple_step_revisions"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "revision_no",
            name="uq_simple_step_revision_execution_no",
        ),
        UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_simple_step_revision_idempotency",
        ),
        CheckConstraint(
            "revision_type IN "
            "('INITIAL', 'AI_REVISION', 'REGENERATE', 'MANUAL_EDIT')",
            name="ck_simple_step_revision_type",
        ),
        CheckConstraint(
            "revision_no > 0",
            name="ck_simple_step_revision_positive",
        ),
        Index(
            "ix_simple_step_revisions_execution_created",
            "execution_id",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    execution_id = Column(
        Integer,
        ForeignKey("simple_step_executions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    revision_no = Column(Integer, nullable=False)
    revision_type = Column(String(24), nullable=False)
    parent_revision_id = Column(
        Integer,
        ForeignKey("simple_step_revisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content = Column(Text, nullable=False)
    structured_content = Column(JsonDocument, nullable=True)
    source_revision_refs = Column(JsonDocument, nullable=False, default=dict)
    skill_run_id = Column(
        Integer,
        ForeignKey("skill_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=False)


class SimpleReviewDecision(Base):
    """Immutable record of a consultant decision on a Simple step revision."""

    __tablename__ = "simple_review_decisions"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_simple_review_decision_idempotency",
        ),
        CheckConstraint(
            "decision IN "
            "('APPROVE', 'REQUEST_REVISION', 'REGENERATE', 'MANUAL_EDIT', 'REOPEN')",
            name="ck_simple_review_decision",
        ),
        CheckConstraint(
            "review_mode IN ('OWNER', 'ADMIN', 'DELEGATED')",
            name="ck_simple_review_decision_review_mode",
        ),
        CheckConstraint(
            "(review_mode = 'OWNER' AND on_behalf_of_user_id IS NULL) "
            "OR (review_mode <> 'OWNER' AND on_behalf_of_user_id IS NOT NULL)",
            name="ck_simple_review_decision_delegation_identity",
        ),
        Index(
            "ix_simple_review_decisions_execution_created",
            "execution_id",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    execution_id = Column(
        Integer,
        ForeignKey("simple_step_executions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_revision_id = Column(
        Integer,
        ForeignKey("simple_step_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision = Column(String(24), nullable=False)
    feedback_text = Column(Text, nullable=True)
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # ``reviewer_id`` always carries the identity a decision is attributed to.
    # ``operator_id`` records who actually performed it, and
    # ``on_behalf_of_user_id`` is mandatory whenever the operator is not the
    # attributed reviewer (admin takeover or explicit delegation).
    review_mode = Column(String(16), nullable=False, default="OWNER")
    operator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    on_behalf_of_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=False)


@event.listens_for(SimpleStepRevision, "before_update")
@event.listens_for(SimpleStepRevision, "before_delete")
def _reject_simple_step_revision_mutation(_mapper, _connection, _target) -> None:
    raise ValueError("simple_step_revision_immutable")


@event.listens_for(SimpleReviewDecision, "before_update")
@event.listens_for(SimpleReviewDecision, "before_delete")
def _reject_simple_review_decision_mutation(_mapper, _connection, _target) -> None:
    raise ValueError("simple_review_decision_immutable")
