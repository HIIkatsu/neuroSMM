"""Database session dependency for FastAPI.

Provides an async SQLAlchemy session per request with automatic cleanup.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConfigurationError


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-request DB session.

    This is a placeholder that must be overridden via
    ``app.dependency_overrides`` at startup with a real session factory.
    """
    raise ConfigurationError("Database session factory not configured")
    yield  # pragma: no cover — makes this a generator

