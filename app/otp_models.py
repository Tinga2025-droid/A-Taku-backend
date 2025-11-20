from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, Enum as SAEnum
from enum import Enum
from .database import Base


class OTPType(str, Enum):
    LOGIN = "LOGIN"
    RESET_PIN = "RESET_PIN"
    KYC = "KYC"
    AGENT = "AGENT"
    USSD = "USSD"


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    phone = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)

    # nova melhoria
    otp_type = Column(SAEnum(OTPType), default=OTPType.LOGIN)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    blocked_until = Column(DateTime, nullable=True)

    meta = Column(JSON, nullable=True)  # device, UA, coordenadas, IP, canal

    consumed = Column(Boolean, default=False)


    # -------- Helpers --------
    def is_blocked(self) -> bool:
        return self.blocked_until and self.blocked_until > datetime.utcnow()

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def mark_used(self, db):
        self.consumed = True
        db.commit()