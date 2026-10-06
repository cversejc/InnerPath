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
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class QAIssue(Base):
    __tablename__ = "qa_issues"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('PROGRAMMATIC', 'VALIDATOR')",
            name="ck_qa_issue_source_type",
        ),
        CheckConstraint(
            "severity IN ('BLOCK', 'MAJOR', 'MINOR')",
            name="ck_qa_issue_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'ACCEPTED', 'DISMISSED')",
            name="ck_qa_issue_status",
        ),
        Index("ix_qa_issues_case_status_severity", "report_case_id", "status", "severity"),
        Index("ix_qa_issues_case_source", "report_case_id", "source_type"),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False
    )
    source_type = Column(String(20), nullable=False)
    source_ref_id = Column(
        Integer, ForeignKey("skill_runs.id", ondelete="RESTRICT"), nullable=True
    )
    issue_type = Column(String(80), nullable=False)
    severity = Column(String(12), nullable=False)
    status = Column(String(12), nullable=False, default="OPEN", index=True)
    target_fragment_key = Column(String(200), nullable=True)
    target_fragment_revision_id = Column(
        Integer,
        ForeignKey("content_fragment_revisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    message = Column(Text, nullable=False)
    evidence_json = Column(JsonDocument, nullable=False, default=dict)
    suggestion = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
