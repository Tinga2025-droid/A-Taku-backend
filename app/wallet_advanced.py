# app/models_advanced.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from .database import Base

class KYC(Base):
    __tablename__ = "kyc"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level = Column(String, default="A")
    status = Column(String, default="pending")
    document_number = Column(String)
    selfie_url = Column(String)
    proof_of_address_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String)
    amount = Column(Float, nullable=True)

    # 🚀 CORREÇÃO AQUI
    extra_data = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    type = Column(String)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)