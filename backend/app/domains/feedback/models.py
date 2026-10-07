from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base, TimestampMixin


class ServiceFeedback(Base, TimestampMixin):
    __tablename__ = "service_feedback"
    __table_args__ = (
        CheckConstraint(
            "(service_request_id IS NOT NULL AND calendar_request_id IS NULL) "
            "OR (service_request_id IS NULL AND calendar_request_id IS NOT NULL)",
            name="ck_service_feedback_one_target",
        ),
        CheckConstraint(
            "feedback_type IN ('PRAISE', 'SUGGESTION', 'COMPLAINT')",
            name="ck_service_feedback_type",
        ),
        CheckConstraint(
            "status IN ('NEW', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_service_feedback_status",
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_service_feedback_rating",
        ),
        UniqueConstraint("service_request_id", name="uq_service_feedback_request"),
        UniqueConstraint("calendar_request_id", name="uq_service_feedback_calendar"),
        Index("ix_service_feedback_status_created", "status", "created_at"),
        Index("ix_service_feedback_user_created", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    service_request_id = Column(
        Integer,
        ForeignKey("service_requests.id", ondelete="RESTRICT"),
        nullable=True,
    )
    calendar_request_id = Column(
        Integer,
        ForeignKey("calendar_requests.id", ondelete="RESTRICT"),
        nullable=True,
    )
    feedback_type = Column(String(20), nullable=False)
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="NEW", index=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
