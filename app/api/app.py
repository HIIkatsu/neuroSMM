"""
FastAPI application factory for NeuroSMM V2.

Creates and configures the ASGI application with route registration,
dependency wiring, and exception handling.

Usage::

    from app.api.app import create_app

    application = create_app()       # used by uvicorn
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.error_handlers import register_exception_handlers
from app.api.routes import channels, drafts, generation, health, projects, publishing
from app.core.config import Settings, get_settings
from app.core.constants import APP_NAME, APP_VERSION
from app.core.logging import get_logger, setup_logging
from app.integrations.db.engine import get_async_engine, get_async_session_factory

logger = get_logger(__name__)


def create_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """Build and return a configured :class:`FastAPI` instance.

    Parameters
    ----------
    settings:
        Optional settings override (used in tests).
    session_factory:
        Optional session factory override (used in tests).
    """
    if settings is None:
        settings = get_settings()

    # ── logging ────────────────────────────────────────────────────
    setup_logging(
        level=settings.log_level.value,
        json_output=settings.log_json,
    )

    # ── database engine ────────────────────────────────────────────
    if session_factory is None:
        db_url = settings.database_url.get_secret_value()
        if db_url:
            engine = get_async_engine(db_url, echo=settings.debug)
            session_factory = get_async_session_factory(engine)

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

    # ── exception handlers ─────────────────────────────────────────
    register_exception_handlers(application)

    # ── dependency overrides for DB session ─────────────────────────
    if session_factory is not None:
        _factory = session_factory

        async def _get_session() -> AsyncGenerator[AsyncSession, None]:
            async with _factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        from app.api.deps.database import get_db_session

        application.dependency_overrides[get_db_session] = _get_session

    # ── settings override for auth dependency ──────────────────────
    if settings is not None:
        _settings = settings

        def _get_settings_override() -> Settings:
            return _settings

        application.dependency_overrides[get_settings] = _get_settings_override

    # ── route registration ─────────────────────────────────────────
    api_prefix = settings.api_prefix
    application.include_router(health.router, prefix=api_prefix)
    application.include_router(projects.router, prefix=api_prefix)
    application.include_router(drafts.router, prefix=api_prefix)
    application.include_router(generation.router, prefix=api_prefix)
    application.include_router(publishing.router, prefix=api_prefix)
    application.include_router(channels.router, prefix=api_prefix)

    logger.info(
        "FastAPI application created",
        extra={"environment": settings.environment.value},
    )

    return application
