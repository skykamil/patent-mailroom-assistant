from fastapi import FastAPI

from app.api.routes import analyses, cases, health
from app.core.config import settings


app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(cases.router)
app.include_router(analyses.router)
