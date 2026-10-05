from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base, TimestampMixin


SERVICE_REQUEST_TYPES = ("report", "calendar")
SERVICE_REQUEST_STATUSES = (
    "submitted",
    "accepted",
    "ai_processing",
    "ai_ready",
    "reviewing",
    "needs_info",
    "failed",
    "delivered",
    "withdrawn",
    "rejected",
)


class ServiceRequest(Base, TimestampMixin):
    """A user request that moves through consultant-assisted delivery."""

    __tablename__ = "service_requests"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_service_request_user_idempotency"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service_type = Column(String(20), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="submitted", index=True)
    request_payload = Column(JSONB, nullable=False)
    idempotency_key = Column(String(128), nullable=True)

    assigned_consultant_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_mingli_consultant_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_psychology_consultant_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    result_type = Column(String(20), nullable=True)
    result_id = Column(Integer, nullable=True)

    needs_info_reason = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)

    accepted_at = Column(DateTime, nullable=True)
    ai_started_at = Column(DateTime, nullable=True)
    ai_completed_at = Column(DateTime, nullable=True)
    reviewing_at = Column(DateTime, nullable=True)
    needs_info_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    def __repr__(self):
        return f"<ServiceRequest(id={self.id}, type={self.service_type}, status={self.status})>"


class ServiceRequestDraft(Base, TimestampMixin):
    """The private AI source and mutable consultant editing copy."""

    __tablename__ = "service_request_drafts"

    id = Column(Integer, primary_key=True)
    request_id = Column(
        Integer,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    ai_payload = Column(JSONB, nullable=False)
    editable_payload = Column(JSONB, nullable=False)
    ai_version = Column(Integer, nullable=False, default=1)
    content_version = Column(Integer, nullable=False, default=1)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ServiceRequestRevision(Base, TimestampMixin):
    """Immutable snapshots used before regeneration and final delivery."""

    __tablename__ = "service_request_revisions"
    __table_args__ = (
        UniqueConstraint("request_id", "version_number", name="uq_service_request_revision_version"),
    )

    id = Column(Integer, primary_key=True)
    request_id = Column(
        Integer,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    stage = Column(String(40), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ServiceRequestTask(Base, TimestampMixin):
    """Celery task state for report and calendar AI draft generation."""

    __tablename__ = "service_request_tasks"

    task_id = Column(String(64), primary_key=True)
    request_id = Column(
        Integer,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="processing", index=True)
    progress = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    input_snapshot = Column(JSONB, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    retry_of_task_id = Column(
        String(64),
        ForeignKey("service_request_tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
