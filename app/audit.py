from .models_advanced import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime

def audit_log(db: Session, user_id: int, action: str, amount: float = None, metadata: str = None):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        amount=amount,
        metadata=metadata,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
