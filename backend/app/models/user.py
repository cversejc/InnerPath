from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base, TimestampMixin


JsonDocument = JSON().with_variant(JSONB, "postgresql")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    wechat_openid = Column(String(100), unique=True, nullable=True, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=True)  # male/female
    birth_year = Column(Integer, nullable=True)
    birth_month = Column(Integer, nullable=True)
    birth_day = Column(Integer, nullable=True)
    birth_is_leap_month = Column(Boolean, nullable=False, default=False)
    birth_hour = Column(Integer, nullable=True)
    birth_minute = Column(Integer, nullable=True)
    birth_place = Column(String(100), nullable=True)
    calendar_type = Column(String(10), nullable=False, default="solar")
    birth_time_precision = Column(String(20), nullable=False, default="unknown")

    # Reusable profile context. Current-state fields are refreshed by the user
    # before a new application; they are never used to rewrite old reports.
    current_residence = Column(String(100), nullable=True)
    marital_status = Column(String(30), nullable=True)
    occupation_status = Column(String(30), nullable=True)
    highest_education = Column(String(30), nullable=True)
    mbti = Column(String(10), nullable=True)
    personality_keywords = Column(JsonDocument, nullable=False, default=list)
    strengths = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    mingli_experience = Column(JsonDocument, nullable=False, default=list)
    mingli_attitude = Column(String(30), nullable=True)
    preferred_content_depth = Column(String(30), nullable=True)
    default_usage_scenarios = Column(JsonDocument, nullable=False, default=list)
    profile_version = Column(Integer, nullable=False, default=1)
    profile_last_confirmed_at = Column(DateTime, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    user_type = Column(String(20), default="explorer", nullable=False)
    role = Column(String(20), default="user", nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    phone_verified_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, phone={self.phone})>"

    @property
    def masked_phone(self):
        """Return masked phone number for privacy"""
        if self.phone and len(self.phone) >= 11:
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        return self.phone

    @property
    def profile_completion(self):
        """Return the percentage of the reusable analytical profile completed."""
        required_values = (
            self.gender,
            self.birth_year,
            self.birth_month,
            self.birth_day,
        )
        completed = sum(value not in (None, "") for value in required_values)
        return int(round(completed / len(required_values) * 100))
