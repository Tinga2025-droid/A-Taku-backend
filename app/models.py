import os
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from .database import Base

class Role(str, Enum):
    USER = "USER"
    AGENT = "AGENT"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    kyc_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0)      # saldo do usuário/cliente
    agent_float = Column(Float, default=0.0)  # e-float (para agentes)
    role = Column(SAEnum(Role), default=Role.USER, nullable=False)
    pin_hash = Column(String, nullable=True)  # para login do AGENTE
    created_at = Column(DateTime, default=datetime.utcnow)

class TxType(str, Enum):
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    CASHOUT = "CASHOUT"
    COMMISSION = "COMMISSION"

class Tx(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    ref = Column(String, unique=True, index=True)
    type = Column(SAEnum(TxType), default=TxType.TRANSFER, nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float, nullable=False)
    meta = Column(String, nullable=True)  # JSON leve
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="OK")

class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, index=True, nullable=False)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False)

class FeesConfig(Base):
    __tablename__ = "fees_config"
    id = Column(Integer, primary_key=True, default=1)
    cashout_fee_pct = Column(Float, default=float(os.getenv("CASHOUT_FEE_PCT", 1.5)))
    cashout_fee_min = Column(Float, default=float(os.getenv("CASHOUT_FEE_MIN", 5)))
    cashout_fee_max = Column(Float, default=float(os.getenv("CASHOUT_FEE_MAX", 150)))
    fee_owner_pct = Column(Float, default=float(os.getenv("FEE_OWNER_PCT", 60)))
