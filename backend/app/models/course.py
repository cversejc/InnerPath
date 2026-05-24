from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DECIMAL, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    cover_image = Column(String(255), nullable=True)

    # Course info
    price = Column(DECIMAL(10, 2), nullable=False)
    original_price = Column(DECIMAL(10, 2), nullable=True)
    total_lessons = Column(Integer, nullable=False)
    duration_hours = Column(DECIMAL(5, 1), nullable=True)

    # Course outline (JSON)
    modules = Column(JSONB, nullable=False)

    # Status
    status = Column(String(20), default="active", nullable=False)  # draft/active/archived
    is_featured = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Course(id={self.id}, title={self.title}, status={self.status})>"


class UserCourse(Base, TimestampMixin):
    __tablename__ = "user_courses"
    __table_args__ = (UniqueConstraint('user_id', 'course_id', name='uq_user_course'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    # Learning progress
    completed_lessons = Column(Integer, default=0, nullable=False)
    progress_percentage = Column(Integer, default=0, nullable=False)
    last_lesson_id = Column(Integer, nullable=True)

    # Purchase info
    purchase_price = Column(DECIMAL(10, 2), nullable=False)
    payment_id = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="active", nullable=False)  # active/completed/expired
    enrolled_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<UserCourse(id={self.id}, user_id={self.user_id}, course_id={self.course_id}, progress={self.progress_percentage}%)>"
