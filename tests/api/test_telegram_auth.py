"""Tests for Telegram init-data based authentication in API requests.

Tests the production Telegram auth path alongside the dev auth path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import quote, urlencode

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.app import create_app
from app.core.config import Environment, Settings
from app.domain.user import User
from app.integrations.db.base import Base
from app.integrations.db.repositories.user import UserRepository

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def _build_init_data(
    *,
    bot_token: str = BOT_TOKEN,
    user_id: int = 111111,
    first_name: str = "Test",
    last_name: str | None = None,
    username: str | None = "testuser",
    language_code: str | None = "en",
    auth_date: int | None = None,
    tamper_hash: bool = False,
) -> str:
    """Build a valid (or intentionally invalid) Telegram init-data string."""
    if auth_date is None:
        auth_date = int(time.time())

    user_obj: dict[str, object] = {"id": user_id, "first_name": first_name}
    if last_name:
        user_obj["last_name"] = last_name
    if username:
        user_obj["username"] = username
    if language_code:
        user_obj["language_code"] = language_code

    params: dict[str, str] = {
        "auth_date": str(auth_date),
        "user": json.dumps(user_obj, separators=(",", ":")),
    }

    data_check_pairs = [f"{k}={params[k]}" for k in sorted(params)]
    data_check_string = "\n".join(data_check_pairs)

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if tamper_hash:
        computed_hash = "a" * 64

    params["hash"] = computed_hash
    return urlencode(params, quote_via=quote)


@pytest.fixture()
async def prod_engine():
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
async def prod_session_factory(prod_engine):
    """Create an async session factory bound to the test engine."""
    return async_sessionmaker(
        bind=prod_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture()
async def prod_app(prod_session_factory):
    """Create a PRODUCTION-environment app with a bot token configured."""
    settings = Settings(
        environment=Environment.PRODUCTION,
        debug=False,
        log_json=False,
        database_url="sqlite+aiosqlite://",
        bot_token=BOT_TOKEN,
    )
    app = create_app(settings=settings, session_factory=prod_session_factory)
    return app


@pytest.fixture()
async def prod_client(prod_app):
    """Create an httpx AsyncClient wired to the production app."""
    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
async def prod_seed_user(prod_session_factory) -> User:
    """Create a test user in the production DB."""
    async with prod_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.create(
            User(telegram_id=111111, username="testuser", first_name="Test")
        )
        await session.commit()
        return user


class TestTelegramAuth:
    """Tests for the Telegram init-data based auth path."""

    async def test_successful_telegram_auth(
        self, prod_client: AsyncClient, prod_seed_user: User
    ) -> None:
        """Valid init-data authenticates and allows access."""
        init_data = _build_init_data(user_id=111111)
        resp = await prod_client.get(
            "/api/v1/projects",
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 200

    async def test_forged_init_data_rejected(
        self, prod_client: AsyncClient
    ) -> None:
        """Tampered init-data hash is rejected with 401."""
        init_data = _build_init_data(tamper_hash=True)
        resp = await prod_client.get(
            "/api/v1/projects",
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    async def test_expired_init_data_rejected(
        self, prod_client: AsyncClient
    ) -> None:
        """Expired init-data is rejected with 401."""
        old_date = int(time.time()) - 200_000
        init_data = _build_init_data(auth_date=old_date)
        resp = await prod_client.get(
            "/api/v1/projects",
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    async def test_missing_credentials_returns_401(
        self, prod_client: AsyncClient
    ) -> None:
        """Request without any auth headers returns 401 in production."""
        resp = await prod_client.get("/api/v1/projects")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    async def test_dev_header_ignored_in_production(
        self, prod_client: AsyncClient, prod_seed_user: User
    ) -> None:
        """X-Dev-User-Id header is ignored in production mode."""
        resp = await prod_client.get(
            "/api/v1/projects",
            headers={"X-Dev-User-Id": str(prod_seed_user.id)},
        )
        assert resp.status_code == 401

    async def test_auto_creates_new_user(
        self, prod_client: AsyncClient
    ) -> None:
        """New Telegram user is auto-created on first auth."""
        init_data = _build_init_data(
            user_id=999888, first_name="NewUser", username="newuser"
        )
        resp = await prod_client.get(
            "/api/v1/projects",
            headers={"X-Telegram-Init-Data": init_data},
        )
        # Should succeed (auto-created user, empty project list)
        assert resp.status_code == 200

    async def test_deactivated_user_rejected(
        self, prod_client: AsyncClient, prod_session_factory
    ) -> None:
        """Deactivated user is rejected even with valid init-data."""
        # Create and deactivate a user
        async with prod_session_factory() as session:
            repo = UserRepository(session)
            user = await repo.create(
                User(telegram_id=555555, username="deact", first_name="Deact")
            )
            deactivated = user.deactivate()
            await repo.update(deactivated)
            await session.commit()

        init_data = _build_init_data(user_id=555555)
        resp = await prod_client.get(
            "/api/v1/projects",
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert resp.status_code == 401
        assert "deactivated" in resp.json()["detail"].lower()


class TestDevAuthStillWorks:
    """Verify that dev auth continues to work in TESTING environment."""

    async def test_dev_header_works_in_testing(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """X-Dev-User-Id works when environment is TESTING."""
        resp = await client.get("/api/v1/projects", headers=auth_headers)
        assert resp.status_code == 200

    async def test_missing_headers_in_testing(
        self, client: AsyncClient
    ) -> None:
        """Missing auth headers return 401 in TESTING too."""
        resp = await client.get("/api/v1/projects")
        assert resp.status_code == 401
