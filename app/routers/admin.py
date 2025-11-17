from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import FeesConfig
from ..schemas import FeesPayload

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/fees")
def set_fees(payload: FeesPayload, db: Session = Depends(get_db)):
    cfg = db.query(FeesConfig).get(1)
    if not cfg:
        cfg = FeesConfig(id=1)
        db.add(cfg)
    cfg.cashout_fee_pct = payload.cashout_fee_pct
    cfg.cashout_fee_min = payload.cashout_fee_min
    cfg.cashout_fee_max = payload.cashout_fee_max
    cfg.fee_owner_pct = payload.fee_owner_pct
    db.commit()
    return {"ok": True}
