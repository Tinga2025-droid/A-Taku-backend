import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ataku.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if DATABASE_URL.startswith("postgresql+psycopg2://"):
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from .models import User
from .auth import hash_password

# ⚠️ Lidos do ambiente (NÃO hardcoded)
ADMIN_PHONE = os.getenv("ADMIN_PHONE")
ADMIN_PIN = os.getenv("ADMIN_PIN")


def ensure_admin_exists(db: Session):
    """
    Garante que existe um ADMIN inicial.
    Usa ADMIN_PHONE/ADMIN_PIN do .env apenas para criar o primeiro admin.
    Em produção, recomenda-se depois alterar o PIN via painel e remover ADMIN_PIN do .env.
    """
    if not ADMIN_PHONE:
        print("[ADMIN] ADMIN_PHONE não definido. Nenhum admin automático será criado.")
        return

    admin = db.query(User).filter(User.phone == ADMIN_PHONE).first()
    if not admin:
        print("[ADMIN] Criando admin inicial...")
        admin = User(
            phone=ADMIN_PHONE,
            full_name="Administrador Geral",
            kyc_level=2,
            is_active=True,
            balance=0.0,
            agent_float=0.0,
            role="ADMIN",  # se Role for Enum, isto continua a funcionar se o tipo for SAEnum
            pin_hash=hash_password(ADMIN_PIN) if ADMIN_PIN else hash_password("1234"),
        )
        db.add(admin)
        db.commit()
        print("[ADMIN] Admin criado.")
    else:
        print("[ADMIN] Admin já existe.")