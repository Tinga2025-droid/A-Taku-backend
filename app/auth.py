import os
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError

# Hash único para todo o sistema (users + agentes)
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT
SECRET = os.getenv("JWT_SECRET", "change-me")
ALGO = "HS256"
ACCESS_EXPIRE_MINUTES = int(os.getenv("ACCESS_EXPIRE_MINUTES", "60"))


def hash_password(plain: str) -> str:
    """Gera hash seguro para PIN/senha."""
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica PIN/senha em texto contra hash armazenado."""
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: int = ACCESS_EXPIRE_MINUTES) -> str:
    """Cria JWT com subject = telefone do usuário."""
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET, algorithm=ALGO)


def decode_token(token: str) -> Optional[str]:
    """Decodifica JWT e devolve o subject (telefone) ou None."""
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload.get("sub")
    except JWTError:
        return None