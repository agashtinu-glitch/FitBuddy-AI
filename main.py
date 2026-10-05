"""FitBuddy FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT, settings
from app.database import Base, engine
from app import models  # noqa: F401 - ensures all tables are registered before create_all
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, description="A student-friendly AI-assisted fitness plan demo.", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "app" / "static")), name="static")
app.include_router(router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "ai_mode": "gemini" if settings.gemini_api_key else "demo"}
