import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///./ataku.db')

if DB_URL.startswith('postgres://'):
    DB_URL = DB_URL.replace('postgres://', 'postgresql://', 1)

if DB_URL.startswith('postgresql://'):
    DB_URL = DB_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)

if DB_URL.startswith('postgresql+psycopg2://'):
    engine = create_engine(
        DB_URL,
        connect_args={'sslmode': 'require'},
        pool_pre_ping=True
    )
else:
    engine = create_engine(
        DB_URL,
        connect_args={'check_same_thread': False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
