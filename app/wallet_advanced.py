# app/wallet_advanced.py
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .models import User
from .models_advanced import Ledger, AuditLog  # só usamos, não definimos aqui
from .audit import audit_log
from .auth import verify_password, hash_password
from .utils import normalize_phone

DEFAULT_PIN = "0000"

# 🔥 Tabela de taxas estilo M-Pesa/Emola, com ~1 MZN a menos
# Ajusta os valores depois se quiser refinar
CASHOUT_TIERS = [
    (0, 100, 3),        # até 100 MZN → taxa 3
    (101, 500, 7),      # 101–500 → 7
    (501, 1000, 12),    # 501–1000 → 12
    (1001, 2000, 19),
    (2001, 5000, 39),
    (5001, 10000, 59),
    (10001, 15000, 79),
    (15001, 20000, 99),
]


def calc_cashout_fee(amount: float) -> float | None:
    """
    Calcula taxa de levantamento com base em faixas fixas.
    Retorna None se o valor estiver fora das faixas.
    """
    for low, high, fee in CASHOUT_TIERS:
        if low <= amount <= high:
            return fee
    return None


def make_transfer(
    db: Session,
    sender_phone: str,
    receiver_phone: str,
    amount: float,
    pin: str,
):
    """
    Transferência interna entre contas A-Taku.
    Usada pelo app / API e pelo USSD.
    """
    try:
        sender_phone = normalize_phone(sender_phone)
        receiver_phone = normalize_phone(receiver_phone)

        sender = db.query(User).filter(User.phone == sender_phone).first()
        receiver = db.query(User).filter(User.phone == receiver_phone).first()

        if not sender:
            return False, "Conta remetente não encontrada."

        if not receiver:
            # Criar conta destino automaticamente
            receiver = User(
                phone=receiver_phone,
                balance=0.0,
                kyc_level=0,
                is_active=True,
                pin_hash=hash_password(DEFAULT_PIN),
                agent_float=0.0,
            )
            db.add(receiver)
            db.commit()
            db.refresh(receiver)

            # usa metadata (mapeia para extra_data)
            audit_log(db, None, "auto_account_created", metadata=receiver_phone)

        if not sender.is_active:
            audit_log(db, sender.id, "transfer_fail_inactive")
            return False, "Conta bloqueada."

        if not receiver.is_active:
            audit_log(db, sender.id, "transfer_fail_destino_inativo")
            return False, "Conta destino bloqueada."

        if sender_phone == receiver_phone:
            return False, "Não pode transferir para si mesmo."

        if amount <= 0:
            return False, "Valor inválido."

        if not verify_password(pin, sender.pin_hash):
            audit_log(db, sender.id, "pin_fail", metadata="transfer")
            return False, "PIN incorreto."

        if sender.balance < amount:
            audit_log(db, sender.id, "transfer_fail_saldo", amount=amount)
            return False, "Saldo insuficiente."

        # Movimentações
        sender.balance -= amount
        receiver.balance += amount

        db.add(
            Ledger(
                user_id=sender.id,
                type="debit",
                amount=amount,
                balance_after=sender.balance,
                created_at=datetime.utcnow(),
            )
        )

        db.add(
            Ledger(
                user_id=receiver.id,
                type="credit",
                amount=amount,
                balance_after=receiver.balance,
                created_at=datetime.utcnow(),
            )
        )

        db.commit()

        audit_log(db, sender.id, "transfer_success", amount=amount)
        audit_log(db, receiver.id, "received_transfer", amount=amount)

        return True, "Transferência concluída."

    except SQLAlchemyError:
        db.rollback()
        return False, "Erro interno ao processar transferência."
