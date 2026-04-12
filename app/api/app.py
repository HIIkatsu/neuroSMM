"""
FastAPI application factory for NeuroSMM V2.

Creates and configures the ASGI application.  Business routers will be
registered in later PRs (PR 05+).

Usage::

    from app.api.app import create_app

    application = create_app()       # used by uvicorn
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.constants import APP_NAME, APP_VERSION
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and return a configured :class:`FastAPI` instance."""
    settings = get_settings()

    # ── logging ────────────────────────────────────────────────────
    setup_logging(
        level=settings.log_level.value,
        json_output=settings.log_json,
    )

    # ── FastAPI instance ───────────────────────────────────────────
    application = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── CORS ───────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── health check ───────────────────────────────────────────────
    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    logger.info(
        "FastAPI application created",
        extra={"environment": settings.environment.value},
    )

    return application
