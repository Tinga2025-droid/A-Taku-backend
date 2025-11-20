# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ataku.db")

# === Correção universal para URLs do Render (postgres:// -> postgresql+psycopg2://) ===
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

# Se vier como postgresql:// sem psycopg2 especificado
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Criar engine conforme o backend
if DATABASE_URL.startswith("postgresql+psycopg2://"):
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},  # necessário no Render
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # necessário p/ SQLite
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()