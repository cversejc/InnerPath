"""Immutable full-text versions produced by the simplified report workflow.

Simple report versions are intentionally independent from ``ReportVersion``:
they carry only the consultant-authored full report text, so the simplified
workflow never touches the analysis, narrative, quality or skill-run assets of
the production pipeline.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)

from app.db.base import Base


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
