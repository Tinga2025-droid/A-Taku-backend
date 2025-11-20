import os, sys

# ⚠️ Garante que o diretório do projeto esteja no caminho de imports
sys.path.append(os.getcwd())

from app.db.database import engine, Base
from app.db import models

print("[DB] Creating tables...")
Base.metadata.create_all(bind=engine)
print("[DB] Done.")
