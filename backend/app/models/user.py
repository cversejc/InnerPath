from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    wechat_openid = Column(String(100), unique=True, nullable=True, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=True)  # male/female
    birth_year = Column(Integer, nullable=True)
    birth_month = Column(Integer, nullable=True)
    birth_day = Column(Integer, nullable=True)
    birth_hour = Column(Integer, nullable=True)
    birth_minute = Column(Integer, nullable=True)
    birth_place = Column(String(100), nullable=True)
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


class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(64), nullable=True)


class StaffInvite(Base, TimestampMixin):
    __tablename__ = "staff_invites"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    accepted_at = Column(DateTime, nullable=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
