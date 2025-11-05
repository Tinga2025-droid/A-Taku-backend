from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, wallet, agent, admin
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="A‑Taku API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(agent.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"ok": True, "service": "A‑Taku API"}
