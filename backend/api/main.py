from fastapi import FastAPI

from backend.api.routers import feedback, health
from backend.common.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(feedback.router)
