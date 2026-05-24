from sqlalchemy import Column, Integer, String, Date, Time, Text, Boolean, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), default="个人能量地图报告", nullable=False)

    # Basic info
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=True)

    # Report content (JSON)
    energy_profile = Column(JSONB, nullable=False)
    career_guidance = Column(JSONB, nullable=False)
    relationship_pattern = Column(JSONB, nullable=False)
    personal_growth = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)

    # AI generated content
    ai_raw_content = Column(Text, nullable=True)
    ai_model = Column(String(50), default="deepseek-chat", nullable=False)

    # Metadata
    generation_time_ms = Column(Integer, nullable=True)
    selected_topics = Column(ARRAY(Text), nullable=True)
    additional_info = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="completed", nullable=False)  # pending/processing/completed/failed
    is_deleted = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Report(id={self.id}, user_id={self.user_id}, status={self.status})>"
