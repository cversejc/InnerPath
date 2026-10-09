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

from app.db.base import Base, TimestampMixin


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class ReportCase(Base, TimestampMixin):
    __tablename__ = "report_cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'ACTIVE', 'BLOCKED', 'READY_TO_DELIVER', 'DELIVERED', 'CANCELLED')",
            name="ck_report_case_status",
        ),
        CheckConstraint(
            "service_request_id IS NULL OR source_report_task_id IS NULL",
            name="ck_report_case_single_source",
        ),
        UniqueConstraint("service_request_id", name="uq_report_case_service_request"),
        UniqueConstraint("source_report_task_id", name="uq_report_case_report_task"),
        Index("ix_report_cases_user_status", "user_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    service_request_id = Column(
        Integer, ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=True
    )
    source_report_task_id = Column(
        String(64),
        ForeignKey("report_tasks.task_id", ondelete="RESTRICT"),
        nullable=True,
    )
    status = Column(String(32), nullable=False, default="CREATED", index=True)
    application_snapshot = Column(JsonDocument, nullable=False)
    application_submitted_at = Column(DateTime, nullable=False)
    workflow_instance_id = Column(
        Integer,
        ForeignKey(
            "workflow_instances.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_report_cases_workflow_instance",
        ),
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    review_policy_version = Column(String(40), nullable=True)


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_key", "version", name="uq_workflow_version_key_version"
        ),
        CheckConstraint("version > 0", name="ck_workflow_version_positive"),
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="ck_workflow_version_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    workflow_key = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="DRAFT", index=True)
    definition_json = Column(JsonDocument, nullable=False)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False)
    published_at = Column(DateTime, nullable=True)


class WorkflowInstance(Base, TimestampMixin):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED', 'RUNNING', 'SUSPENDED', 'COMPLETED', 'CANCELLED')",
            name="ck_workflow_instance_status",
        ),
        Index("ix_workflow_instances_case_status", "report_case_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer,
        ForeignKey("report_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    workflow_version_id = Column(
        Integer, ForeignKey("workflow_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status = Column(String(20), nullable=False, default="CREATED", index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    suspended_at = Column(DateTime, nullable=True)


class StepTask(Base, TimestampMixin):
    __tablename__ = "step_tasks"
    __table_args__ = (
        UniqueConstraint(
            "workflow_instance_id", "step_key", name="uq_step_task_instance_key"
        ),
        CheckConstraint(
            "executor IN ('HUMAN', 'AI', 'HYBRID')", name="ck_step_task_executor"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'READY', 'EXECUTING', 'WAITING_REVIEW', 'IN_REVIEW', "
            "'NEEDS_REVISION', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_step_task_status",
        ),
        CheckConstraint("sequence_no > 0", name="ck_step_task_sequence_positive"),
        CheckConstraint(
            "activation_no >= 0", name="ck_step_task_activation_nonnegative"
        ),
        Index("ix_step_tasks_workflow_status", "workflow_instance_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    workflow_instance_id = Column(
        Integer, ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False
    )
    step_key = Column(String(100), nullable=False)
    sequence_no = Column(Integer, nullable=False)
    executor = Column(String(20), nullable=False)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    required_capability = Column(String(100), nullable=True)
    assignee_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    activation_no = Column(Integer, nullable=False, default=0)
    config_snapshot = Column(JsonDocument, nullable=False)
    result_json = Column(JsonDocument, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class WorkflowOutbox(Base):
    __tablename__ = "workflow_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PUBLISHED', 'FAILED')",
            name="ck_workflow_outbox_status",
        ),
        Index("ix_workflow_outbox_pending", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload_json = Column(JsonDocument, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)
    published_at = Column(DateTime, nullable=True)
