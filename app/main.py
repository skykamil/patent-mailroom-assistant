from fastapi import FastAPI

from app.api.routes import analyses, cases, health, reviews
from app.core.config import settings


app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(cases.router)
app.include_router(analyses.router)
app.include_router(reviews.router)
