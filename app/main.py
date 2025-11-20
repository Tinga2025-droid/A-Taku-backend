from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, auth_otp, wallet, agent, admin, ussd


app = FastAPI(
    title="A-Taku API",
    version="2.0.0",
    description="Sistema de carteira digital A-Taku — transfers, cashout, agentes, OTP e USSD"
)


# ------------------------------
# 📌 Setup inicial da base de dados
# ------------------------------
@app.on_event("startup")
def init_db():
    """
    Cria tabelas caso não existam.
    Em produção é recomendado usar migrations (Alembic),
    mas para now este auto-setup evita erros de deploy.
    """
    Base.metadata.create_all(bind=engine)


# ------------------------------
# 🔧 CORS
# ------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Pode trocar para domínio do app / mobile
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------
# 📌 Routers (ordem importa!)
# ------------------------------
app.include_router(auth.router)       # OTP + Login
app.include_router(auth_otp.router)   # Login alternativo com verificação OTP
app.include_router(wallet.router)     # Enviar, saldo, extrato
app.include_router(agent.router)      # Depósito/cashout via agentes
app.include_router(admin.router)      # Painel admin futuro
app.include_router(ussd.router)       # USSD *229#


# ------------------------------
# 🔍 Rotas públicas
# ------------------------------
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "A-Taku API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/healthz")
def health_check():
    return {"ok": True, "status": "UP"}