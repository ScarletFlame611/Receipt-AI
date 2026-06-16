"""Сборка FastAPI-приложения
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api import (
    routes_admin, routes_analytics, routes_auth, routes_meta, routes_receipts,
)
from src.api.dependencies import is_pipeline_loaded, pipeline_components, warmup_pipeline
from src.db.base import Base, engine
from src.utils.config import configs, settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    if settings.app_env != "test":
        warmup_pipeline()
    yield


app = FastAPI(title=configs.app.app.name, version=configs.app.app.version, lifespan=lifespan)

if configs.app.app.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configs.app.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(routes_auth.router)
app.include_router(routes_receipts.router)
app.include_router(routes_analytics.router)
app.include_router(routes_admin.router)
app.include_router(routes_meta.router)


@app.get("/api/health", tags=["health"])
def health():
    loaded = is_pipeline_loaded()
    body = {
        "status": "ok" if loaded else "loading",
        "pipeline_loaded": loaded,
        "components": pipeline_components(),
        "version": configs.app.app.version,
    }
    code = status.HTTP_200_OK if loaded else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body)
