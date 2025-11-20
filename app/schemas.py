from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- Auth / OTP ----------
class OTPRequest(BaseModel):
    phone: str


class LoginRequest(BaseModel):
    phone: str
    otp: str
    pin: str


class TokenResponse(BaseModel):
    token: str


# ---------- Wallet ----------
class BalanceResponse(BaseModel):
    balance: float


class SendRequest(BaseModel):
    to: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class TransferRequest(BaseModel):
    receiver: str
    amount: float = Field(gt=0)
    pin: str


class TxItem(BaseModel):
    ref: str
    amount: float
    created_at: datetime
    direction: str  # IN | OUT


class HistoryResponse(BaseModel):
    items: List[TxItem]


# ---------- Agent / Cashin-Cashout ----------
class AgentLoginRequest(BaseModel):
    phone: str
    pin: str


class DepositRequest(BaseModel):
    customer_phone: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class CashoutRequest(BaseModel):
    customer_phone: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None


class FeesPayload(BaseModel):
    cashout_fee_pct: float
    cashout_fee_min: float
    cashout_fee_max: float
    fee_owner_pct: float
