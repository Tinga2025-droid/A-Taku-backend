import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from .models import User
from .auth import hash_password

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


def ensure_admin_exists(db: Session):
    admin_phone = "+258879512430"
    admin_pin = "4829"

    admin = db.query(User).filter(User.phone == admin_phone).first()
    if not admin:
        admin = User(
            phone=admin_phone,
            full_name="Administrador Geral",
            kyc_level=2,
            is_active=True,
            balance=0.0,
            agent_float=0.0,
            role="ADMIN",
            pin_hash=hash_password(admin_pin),
        )
        db.add(admin)
        db.commit()