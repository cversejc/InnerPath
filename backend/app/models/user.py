from sqlalchemy import Column, Integer, String, Boolean
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
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, phone={self.phone})>"

    @property
    def masked_phone(self):
        """Return masked phone number for privacy"""
        if self.phone and len(self.phone) >= 11:
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        return self.phone
