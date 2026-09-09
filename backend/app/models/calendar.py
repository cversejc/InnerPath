from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


class UserCalendar(Base, TimestampMixin):
    __tablename__ = "user_calendars"
    __table_args__ = (UniqueConstraint("series_id", "version_number", name="uq_user_calendar_series_version"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    series_id = Column(String(36), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    title = Column(String(150), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    published_at = Column(DateTime, nullable=True)


class CalendarEntry(Base, TimestampMixin):
    __tablename__ = "calendar_entries"
    __table_args__ = (UniqueConstraint("calendar_id", "entry_date", name="uq_calendar_entry_date"),)

    id = Column(Integer, primary_key=True, index=True)
    calendar_id = Column(Integer, ForeignKey("user_calendars.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    day_pillar = Column(String(20), nullable=True)
    tone = Column(String(20), nullable=True)
    status_label = Column(String(100), nullable=True)
    keyword = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)
    suitable = Column(JSONB, nullable=False, default=list)
    unsuitable = Column(JSONB, nullable=False, default=list)
    time_window = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)


class DecisionLog(Base, TimestampMixin):
    """A user's real-world action or decision captured against a calendar date."""

    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    kind = Column(String(20), nullable=False, default="action")
    status = Column(String(20), nullable=False, default="done")
    content = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
