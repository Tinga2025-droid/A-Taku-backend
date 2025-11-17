
from .routers import auth_otp

app.include_router(auth_otp.router)
