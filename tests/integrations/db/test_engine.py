"""
Tests for the async engine and session factory.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.integrations.db.engine import get_async_engine, get_async_session_factory


class TestEngine:
    def test_get_async_engine_creates_engine(self) -> None:
        engine = get_async_engine("sqlite+aiosqlite://")
        assert isinstance(engine, AsyncEngine)

    def test_get_async_engine_echo(self) -> None:
        engine = get_async_engine("sqlite+aiosqlite://", echo=True)
        assert engine.echo is True

    async def test_session_factory_produces_sessions(self) -> None:
        engine = get_async_engine("sqlite+aiosqlite://")
        factory = get_async_session_factory(engine)
        async with factory() as session:
            assert isinstance(session, AsyncSession)
        await engine.dispose()
