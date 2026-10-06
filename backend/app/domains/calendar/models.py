from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


class UserCalendar(Base, TimestampMixin):
    __tablename__ = "user_calendars"
    __table_args__ = (
        UniqueConstraint("series_id", "version_number", name="uq_user_calendar_series_version"),
        # A series keeps at most one published version so users always resolve a single active calendar.
        Index(
            "uq_user_calendar_current_published",
            "series_id",
            unique=True,
            postgresql_where=text("status = 'published'"),
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(Integer, ForeignKey("service_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    source_report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    series_id = Column(String(36), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    title = Column(String(150), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    meta_payload = Column(JSONB, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    published_at = Column(DateTime, nullable=True)
    calendar_request_id = Column(Integer, ForeignKey("calendar_requests.id", ondelete="SET NULL"), nullable=True, index=True)


class CalendarRequest(Base, TimestampMixin):
    """A user-submitted request for a new decision calendar."""

    __tablename__ = "calendar_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_version = Column(Integer, nullable=False, default=1)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    focus_topics = Column(JSONB, nullable=False, default=list)
    usage_scenario = Column(String(50), nullable=True)
    goal = Column(Text, nullable=True)
    decision_description = Column(Text, nullable=True)
    expected_outcomes = Column(JSONB, nullable=False, default=list)
    additional_info = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    task_id = Column(String(64), nullable=True, index=True)
    progress = Column(Integer, nullable=False, default=0)
    generation_error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    input_snapshot = Column(JSONB, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)


class CalendarEntry(Base, TimestampMixin):
    __tablename__ = "calendar_entries"
    __table_args__ = (UniqueConstraint("calendar_id", "entry_date", name="uq_calendar_entry_date"),)

    id = Column(Integer, primary_key=True)
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

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    kind = Column(String(20), nullable=False, default="action")
    status = Column(String(20), nullable=False, default="done")
    content = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
