from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# ============================================================
# 🔹 VALIDADORES DE USO GERAL
# ============================================================

def validate_phone(v: str) -> str:
    if not v.startswith("+258"):
        raise ValueError("O número deve começar com +258")
    if len(v) < 12 or len(v) > 13:
        raise ValueError("Número inválido")
    if not v[1:].isdigit():
        raise ValueError("Número deve conter apenas dígitos após +258")
    return v


def validate_pin(v: str) -> str:
    if len(v) != 4 or not v.isdigit():
        raise ValueError("PIN deve conter exatamente 4 dígitos")
    if v in ["0000", "1111", "1234", "2222", "3333", "4444",
             "5555", "6666", "7777", "8888", "9999"]:
        raise ValueError("PIN demasiado fraco. Escolha outro.")
    return v


# ============================================================
# 🔹 AUTH / OTP
# ============================================================

class OTPRequest(BaseModel):
    phone: str

    _phone_validator = validator("phone", allow_reuse=True)(validate_phone)


class LoginRequest(BaseModel):
    phone: str
    otp: str
    pin: str

    _phone_validator = validator("phone", allow_reuse=True)(validate_phone)
    _pin_validator = validator("pin", allow_reuse=True)(validate_pin)


class TokenResponse(BaseModel):
    token: str


# ============================================================
# 🔹 WALLET
# ============================================================

class BalanceResponse(BaseModel):
    balance: float


class SendRequest(BaseModel):
    to: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None

    _phone_validator = validator("to", allow_reuse=True)(validate_phone)


class TransferRequest(BaseModel):
    receiver: str
    amount: float = Field(gt=0)
    pin: str

    _phone_validator = validator("receiver", allow_reuse=True)(validate_phone)
    _pin_validator = validator("pin", allow_reuse=True)(validate_pin)


class TxItem(BaseModel):
    ref: str
    amount: float
    created_at: datetime
    direction: str  # IN | OUT


class HistoryResponse(BaseModel):
    items: List[TxItem]


# ============================================================
# 🔹 AGENT / CASH-IN / CASH-OUT
# ============================================================

class AgentLoginRequest(BaseModel):
    phone: str
    pin: str

    _phone_validator = validator("phone", allow_reuse=True)(validate_phone)
    _pin_validator = validator("pin", allow_reuse=True)(validate_pin)


class DepositRequest(BaseModel):
    customer_phone: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None

    _phone_validator = validator("customer_phone", allow_reuse=True)(validate_phone)


class CashoutRequest(BaseModel):
    customer_phone: str
    amount: float = Field(gt=0)
    idempotency_key: Optional[str] = None

    _phone_validator = validator("customer_phone", allow_reuse=True)(validate_phone)


# ============================================================
# 🔹 FEES / ADMIN
# ============================================================

class FeesPayload(BaseModel):
    cashout_fee_pct: float = Field(ge=0, le=30)
    cashout_fee_min: float = Field(ge=0)
    cashout_fee_max: float = Field(gt=0)
    fee_owner_pct: float = Field(ge=0, le=100)

    @validator("cashout_fee_max")
    def validate_max_vs_min(cls, v, values):
        if "cashout_fee_min" in values and v < values["cashout_fee_min"]:
            raise ValueError("cashout_fee_max não pode ser menor que cashout_fee_min")
        return v