from sqlalchemy import Column, Integer, String, Date, Time, Text, Boolean, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from app.config import settings
from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), default="辰鉴·人生说明书", nullable=False)

    # Basic info
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=True)
    birth_calendar_type = Column(String(10), nullable=False, default="solar")
    birth_place = Column(String(100), nullable=True)
    input_snapshot = Column(JSONB, nullable=True)

    # Report content (JSON)
    energy_profile = Column(JSONB, nullable=False)
    career_guidance = Column(JSONB, nullable=False)
    relationship_pattern = Column(JSONB, nullable=False)
    personal_growth = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)

    # AI generated content
    ai_raw_content = Column(Text, nullable=True)
    ai_model = Column(String(50), default=settings.DEEPSEEK_MODEL, nullable=False)

    # Metadata
    generation_time_ms = Column(Integer, nullable=True)
    selected_topics = Column(ARRAY(Text), nullable=True)
    additional_info = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="completed", nullable=False)  # pending/processing/completed/failed
    is_deleted = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Report(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ReportTask(Base, TimestampMixin):
    __tablename__ = "report_tasks"

    task_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="processing", index=True)
    progress = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
