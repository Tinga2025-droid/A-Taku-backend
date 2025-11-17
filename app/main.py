from fastapi import FastAPI
from .routers import auth_otp
from fastapi.middleware.cors import CORSMiddleware
from .routers import ussd, auth, wallet, agent, admin
from .database import Base, engine

app = FastAPI(title="A-Taku API", version="1.0.0")

@app.on_event("startup")
def init_db():
    Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(agent.router)
app.include_router(admin.router)
app.include_router(ussd.router)
app.include_router(auth_otp.router)

@app.get("/")
def root():
    return {"ok": True, "service": "A-Taku API"}

@app.get("/healthz")
def health_check():
    return {"ok": True}# redeploy fix 11/17/2025 14:05:20
