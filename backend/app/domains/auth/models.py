from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.base import Base, TimestampMixin


class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(64), nullable=True)


class StaffInvite(Base, TimestampMixin):
    __tablename__ = "staff_invites"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    consultant_type = Column(String(20), nullable=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    accepted_at = Column(DateTime, nullable=True)
