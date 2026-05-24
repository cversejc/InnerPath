from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, ARRAY, DECIMAL
from app.db.base import Base, TimestampMixin


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Service info
    service_type = Column(String(50), nullable=False)  # trial/basic/advanced
    service_name = Column(String(100), nullable=False)
    service_price = Column(DECIMAL(10, 2), nullable=True)

    # Booking info
    preferred_time = Column(String(50), nullable=False)
    confirmed_date = Column(Date, nullable=True)
    confirmed_time = Column(Time, nullable=True)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    consultant_name = Column(String(50), nullable=True)

    # User info
    contact_phone = Column(String(20), nullable=False)
    topics = Column(ARRAY(Text), nullable=False)
    notes = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending/confirmed/completed/cancelled
    cancellation_reason = Column(Text, nullable=True)

    # Meeting info
    meeting_url = Column(String(255), nullable=True)
    meeting_notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Booking(id={self.id}, user_id={self.user_id}, service_type={self.service_type}, status={self.status})>"
