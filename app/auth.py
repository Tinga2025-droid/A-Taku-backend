from datetime import datetime, timedelta
from jose import jwt, JWTError
import os

SECRET = os.getenv("JWT_SECRET", "change-me")
ALGO = "HS256"
ACCESS_MIN = int(os.getenv("ACCESS_EXPIRE_MINUTES", "1440"))

def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_MIN)
    to_encode = {"sub": subject, "exp": int(expire.timestamp())}
    return jwt.encode(to_encode, SECRET, algorithm=ALGO)

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload.get("sub")
    except JWTError:
        return None
