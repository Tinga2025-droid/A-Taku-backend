# app/audit.py
from datetime import datetime
from sqlalchemy.orm import Session

from .models_advanced import AuditLog


def audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    amount: float | None = None,
    metadata: str | None = None,
) -> None:
    """
    Registo centralizado de auditoria (transações, falhas de PIN, etc.).
    extra_data na tabela = metadata aqui.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        amount=amount,
        extra_data=metadata,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()