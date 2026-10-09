"""Whole-node checks/signatures; historical per-item revisions remain intact."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from app.db.base import Base
from app.domains.workflow.models import JsonDocument

POLICY_VERSION = "six-node-review-v1"


class NodeReviewState(Base):
    __tablename__ = "node_review_states"
    __table_args__ = (UniqueConstraint("report_case_id", "step_key", name="uq_node_review_state"),)
    id = Column(Integer, primary_key=True)
    report_case_id = Column(Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False)
    step_key = Column(String(8), nullable=False)
    metadata_json = Column(JsonDocument, nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False)


class NodeReviewCommand(Base):
    __tablename__ = "node_review_commands"
    __table_args__ = (UniqueConstraint("report_case_id", "idempotency_key", name="uq_node_review_command"),)
    id = Column(Integer, primary_key=True)
    report_case_id = Column(Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False, index=True)
    step_task_id = Column(Integer, ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False)
    kind = Column(String(16), nullable=False)
    idempotency_key = Column(String(160), nullable=False)
    activation_no = Column(Integer, nullable=False)
    fingerprint = Column(String(64), nullable=False)
    policy_version = Column(String(40), nullable=False)
    status = Column(String(16), nullable=False, default="PENDING")
    input_json = Column(JsonDocument, nullable=False)
    output_json = Column(JsonDocument, nullable=True)
    model_trace = Column(JsonDocument, nullable=True)
    error = Column(String(500), nullable=True)
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class NodeApproval(Base):
    __tablename__ = "node_approvals"
    __table_args__ = (UniqueConstraint("report_case_id", "step_task_id", "activation_no", "fingerprint", name="uq_node_approval_version"),)
    id = Column(Integer, primary_key=True)
    report_case_id = Column(Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False)
    step_task_id = Column(Integer, ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False)
    activation_no = Column(Integer, nullable=False)
    fingerprint = Column(String(64), nullable=False)
    policy_version = Column(String(40), nullable=False)
    check_command_id = Column(Integer, ForeignKey("node_review_commands.id", ondelete="RESTRICT"), nullable=False)
    manifest_json = Column(JsonDocument, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_at = Column(DateTime, nullable=False)


class NodeCheckpointApproval(Base):
    __tablename__ = "node_checkpoint_approvals"
    __table_args__ = (
        UniqueConstraint("report_case_id", "idempotency_key", name="uq_node_checkpoint_idempotency"),
        UniqueConstraint(
            "report_case_id", "step_task_id", "activation_no", "checkpoint_key", "fingerprint",
            name="uq_node_checkpoint_version",
        ),
    )
    id = Column(Integer, primary_key=True)
    report_case_id = Column(Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False, index=True)
    step_task_id = Column(Integer, ForeignKey("step_tasks.id", ondelete="RESTRICT"), nullable=False)
    activation_no = Column(Integer, nullable=False)
    checkpoint_key = Column(String(32), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    policy_version = Column(String(40), nullable=False)
    idempotency_key = Column(String(160), nullable=False)
    manifest_json = Column(JsonDocument, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_at = Column(DateTime, nullable=False)
