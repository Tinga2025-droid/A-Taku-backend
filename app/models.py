import os
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Boolean,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from .database import Base


# ---------------------------------------
# ROLES DO SISTEMA
# ---------------------------------------
class Role(str, Enum):
    USER = "USER"
    AGENT = "AGENT"
    ADMIN = "ADMIN"


# ---------------------------------------
# UTILIZADORES (User = cliente + agente + admin)
# ---------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)

    # Wallet
    balance = Column(Float, default=0.0)

    # Agente
    agent_code = Column(String, unique=True, nullable=True)
    agent_float = Column(Float, default=0.0)

    # Segurança
    role = Column(SAEnum(Role), default=Role.USER, nullable=False)
    pin_hash = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    kyc_level = Column(Integer, default=0)
    pin_fail_count = Column(Integer, default=0)
    pin_lock_until = Column(DateTime, nullable=True)

    # Anti-fraude
    last_tx_at = Column(DateTime, nullable=True)
    tx_rate_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relações
    sent_txs = relationship("Tx", foreign_keys="Tx.from_user_id")
    received_txs = relationship("Tx", foreign_keys="Tx.to_user_id")


# ---------------------------------------
# TIPOS DE TRANSAÇÕES
# ---------------------------------------
class TxType(str, Enum):
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    CASHOUT = "CASHOUT"
    COMMISSION = "COMMISSION"


# ---------------------------------------
# TRANSAÇÕES
# ---------------------------------------
class Tx(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    ref = Column(String, unique=True, index=True)

    type = Column(SAEnum(TxType), nullable=False, default=TxType.TRANSFER)

    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    amount = Column(Float, nullable=False)
    meta = Column(String, nullable=True)

    status = Column(String, default="OK")
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------
# OTP
# ---------------------------------------
class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, index=True, nullable=False)
    code = Column(String, nullable=False)

    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False)


# ---------------------------------------
# CONFIGURAÇÃO DE TAXAS
# ---------------------------------------
class FeesConfig(Base):
    __tablename__ = "fees_config"

    id = Column(Integer, primary_key=True, default=1)

    cashout_fee_pct = Column(Float, default=float(os.getenv("CASHOUT_FEE_PCT", 1.5)))
    cashout_fee_min = Column(Float, default=float(os.getenv("CASHOUT_FEE_MIN", 5)))
    cashout_fee_max = Column(Float, default=float(os.getenv("CASHOUT_FEE_MAX", 150)))

    fee_owner_pct = Column(Float, default=float(os.getenv("FEE_OWNER_PCT", 60)))
