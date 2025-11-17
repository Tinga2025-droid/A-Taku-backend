from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Integer
from .database import Base

class OTPCode(Base):
    __tablename__ = "otp_codes"

    phone = Column(String, primary_key=True, index=True)
    otp = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    attempts = Column(Integer, default=0)
    blocked_until = Column(DateTime, nullable=True)

    def is_blocked(self):
        return self.blocked_until and self.blocked_until > datetime.utcnow()

    def is_expired(self):
        return self.created_at < datetime.utcnow() - timedelta(minutes=5)
