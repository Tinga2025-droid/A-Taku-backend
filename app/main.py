from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from time import sleep

from .database import Base, engine, SessionLocal, ensure_admin_exists
from .routers import auth, auth_otp, wallet, agent, admin, ussd

app = FastAPI(
    title="A-Taku API",
    version="2.0.0",
    description="Sistema de carteira digital A-Taku — transfers, cashout, agentes, OTP e USSD"
)

def safe_init_db():
    max_retries = 30
    delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            ensure_admin_exists(db)
            db.close()
            print("[INIT] Banco pronto e admin verificado.")
            return
        except OperationalError:
            print(f"[INIT] Postgres não está pronto ({attempt}/{max_retries})…")
            sleep(delay)

    raise RuntimeError("Falha ao conectar ao Postgres após várias tentativas.")

@app.on_event("startup")
def on_startup():
    safe_init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(auth_otp.router)
app.include_router(wallet.router)
app.include_router(agent.router)
app.include_router(admin.router)
app.include_router(ussd.router)

@app.get("/")
def root():
    return {
        "ok": True,
        "service": "A-Taku API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.head("/")
def head_root():
    return {}

@app.get("/healthz")
def health_check():
    return {"ok": True, "status": "UP"}