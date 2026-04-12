"""
Shared pytest fixtures for database integration tests.

Provides an in-memory async SQLite engine and per-test sessions so that
every test starts with a clean schema and is fully isolated.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.integrations.db.base import Base


@pytest.fixture()
async def async_engine():
    """Create an in-memory async SQLite engine with all tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def async_session(async_engine):
    """Provide a per-test async session that is rolled back after each test."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
