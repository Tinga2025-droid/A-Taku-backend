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
    Base.metadata.create_all(bind=engine)

# ------------------------------
# 🔧 CORS
# ------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# 📌 Routers
# ------------------------------
app.include_router(auth.router)
app.include_router(auth_otp.router)
app.include_router(wallet.router)
app.include_router(agent.router)
app.include_router(admin.router)
app.include_router(ussd.router)

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

@app.head("/")
def head_root():
    """Necessário para Render não retornar 405 e reiniciar o serviço"""
    return {}

@app.get("/healthz")
def health_check():
    return {"ok": True, "status": "UP"}
