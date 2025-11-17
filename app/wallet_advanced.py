from sqlalchemy.orm import Session
from .models import User
from .models_advanced import Ledger
from .audit import audit_log
from datetime import datetime

def make_transfer(db: Session, sender_phone: str, receiver_phone: str, amount: float, pin: str):

    sender = db.query(User).filter(User.phone == sender_phone).first()
    receiver = db.query(User).filter(User.phone == receiver_phone).first()

    if not sender:
        return False, "Conta remetente não encontrada."

    if not receiver:
        return False, "Conta destino não encontrada."

    if sender.pin != pin:
        audit_log(db, sender.id, "pin_fail", metadata="transfer")
        return False, "PIN incorreto."

    if sender.balance < amount:
        audit_log(db, sender.id, "transfer_fail_saldo", amount=amount)
        return False, "Saldo insuficiente."

    sender.balance -= amount
    receiver.balance += amount

    # Ledger entries
    debit = Ledger(
        user_id=sender.id,
        type="debit",
        amount=amount,
        balance_after=sender.balance,
        created_at=datetime.utcnow()
    )
    db.add(debit)

    credit = Ledger(
        user_id=receiver.id,
        type="credit",
        amount=amount,
        balance_after=receiver.balance,
        created_at=datetime.utcnow()
    )
    db.add(credit)

    db.commit()

    audit_log(db, sender.id, "transfer_success", amount=amount)
    audit_log(db, receiver.id, "received_transfer", amount=amount)

    return True, "Transferência concluída."
