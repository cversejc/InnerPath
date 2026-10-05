from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class ReportVersion(Base):
    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint(
            "report_case_id", "version_no", name="uq_report_version_case_version"
        ),
    )

    id = Column(Integer, primary_key=True)
    report_case_id = Column(
        Integer, ForeignKey("report_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_no = Column(Integer, nullable=False)
    workflow_version_id = Column(
        Integer, ForeignKey("workflow_versions.id", ondelete="RESTRICT"), nullable=False
    )
    narrative_plan_id = Column(
        Integer, ForeignKey("narrative_plans.id", ondelete="RESTRICT"), nullable=False
    )
    fragment_snapshot = Column(JsonDocument, nullable=False)
    semantic_snapshot = Column(JsonDocument, nullable=False)
    structured_data = Column(JsonDocument, nullable=False)
    rendered_html = Column(Text, nullable=False)
    pdf_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False)
    delivered_at = Column(DateTime, nullable=False)


@event.listens_for(ReportVersion, "before_update")
@event.listens_for(ReportVersion, "before_delete")
def _reject_report_version_mutation(_mapper, _connection, _target) -> None:
    raise ValueError("report_version_immutable")
