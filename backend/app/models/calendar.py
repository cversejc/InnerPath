from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


class UserCalendar(Base, TimestampMixin):
    __tablename__ = "user_calendars"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
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
