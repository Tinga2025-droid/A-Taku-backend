# app/audit.py
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json

from .models_advanced import AuditLog


def sanitize_metadata(metadata):
    """
    Garante que metadata nunca quebre o banco.
    Se vier dict/list → converte para JSON seguro.
    Se vier algo estranho → converte para string limpa.
    """
    if metadata is None:
        return None

    try:
        if isinstance(metadata, (dict, list)):
            return json.dumps(metadata, ensure_ascii=False)
        return str(metadata)
    except Exception:
        return "INVALID_METADATA"


def audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    amount: float | None = None,
    metadata: str | dict | list | None = None,
) -> None:
    """
    Auditoria centralizada — NUNCA deve quebrar operações principais.
    Se falhar, apenas imprime aviso e não lança exceção.
    """

    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            amount=amount,
            extra_data=sanitize_metadata(metadata),
            created_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()

    except SQLAlchemyError as e:
        # Nunca interrompe a operação principal
        db.rollback()
        print(f"[AUDIT-ERROR] Falha ao gravar auditoria: {e}")

    except Exception as e:
        print(f"[AUDIT-UNEXPECTED] Erro inesperado na auditoria: {e}")
