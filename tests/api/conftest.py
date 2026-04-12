"""Shared fixtures for API integration tests.

Provides a test FastAPI app backed by an in-memory SQLite database,
an httpx AsyncClient, and helper factories for seeding test data.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.app import create_app
from app.core.config import Environment, Settings
from app.domain.user import User
from app.integrations.db.base import Base
from app.integrations.db.repositories.user import UserRepository


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
async def session_factory(async_engine):
    """Create an async session factory bound to the test engine."""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture()
async def test_app(session_factory):
    """Create a test FastAPI app with in-memory DB."""
    settings = Settings(
        environment=Environment.TESTING,
        debug=True,
        log_json=False,
        database_url="sqlite+aiosqlite://",
    )
    app = create_app(settings=settings, session_factory=session_factory)
    return app


@pytest.fixture()
async def client(test_app):
    """Create an httpx AsyncClient wired to the test app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
async def seed_user(session_factory) -> User:
    """Create and return a test user in the DB."""
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.create(
            User(telegram_id=111111, username="testuser", first_name="Test")
        )
        await session.commit()
        return user


@pytest.fixture()
async def seed_user_b(session_factory) -> User:
    """Create and return a second test user in the DB."""
    async with session_factory() as session:
        repo = UserRepository(session)
        user = await repo.create(
            User(telegram_id=222222, username="otheruser", first_name="Other")
        )
        await session.commit()
        return user


@pytest.fixture()
def auth_headers(seed_user) -> dict[str, str]:
    """Return headers with the dev auth header for seed_user."""
    return {"X-Dev-User-Id": str(seed_user.id)}


@pytest.fixture()
def auth_headers_b(seed_user_b) -> dict[str, str]:
    """Return headers with the dev auth header for seed_user_b."""
    return {"X-Dev-User-Id": str(seed_user_b.id)}
