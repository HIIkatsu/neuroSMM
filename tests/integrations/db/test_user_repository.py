"""
Tests for User repository — create / load / update round-trip,
domain-type correctness, and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.exceptions import NotFoundError
from app.domain.user import User
from app.integrations.db.repositories.user import UserRepository

# ── helpers ────────────────────────────────────────────────────────────

def _make_user(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "telegram_id": 111222333,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "en",
    }
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]


# ── create ─────────────────────────────────────────────────────────────


class TestUserCreate:
    async def test_create_assigns_id(self, async_session) -> None:
        repo = UserRepository(async_session)
        user = _make_user()
        saved = await repo.create(user)

        assert saved.id is not None
        assert saved.id > 0

    async def test_create_preserves_fields(self, async_session) -> None:
        repo = UserRepository(async_session)
        user = _make_user(
            telegram_id=999,
            username="alice",
            first_name="Alice",
            last_name="Smith",
            language_code="ru",
        )
        saved = await repo.create(user)

        assert saved.telegram_id == 999
        assert saved.username == "alice"
        assert saved.first_name == "Alice"
        assert saved.last_name == "Smith"
        assert saved.language_code == "ru"
        assert saved.is_active is True

    async def test_create_returns_domain_model(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        assert isinstance(saved, User)


# ── get by id ──────────────────────────────────────────────────────────


class TestUserGetById:
    async def test_get_by_id_returns_matching_user(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]

        assert loaded.id == saved.id
        assert loaded.telegram_id == saved.telegram_id

    async def test_get_by_id_not_found(self, async_session) -> None:
        repo = UserRepository(async_session)
        with pytest.raises(NotFoundError, match="not found"):
            await repo.get_by_id(99999)

    async def test_get_by_id_returns_domain_model(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert isinstance(loaded, User)


# ── get by telegram_id ─────────────────────────────────────────────────


class TestUserGetByTelegramId:
    async def test_get_by_telegram_id(self, async_session) -> None:
        repo = UserRepository(async_session)
        await repo.create(_make_user(telegram_id=42))
        loaded = await repo.get_by_telegram_id(42)
        assert loaded.telegram_id == 42

    async def test_get_by_telegram_id_not_found(self, async_session) -> None:
        repo = UserRepository(async_session)
        with pytest.raises(NotFoundError):
            await repo.get_by_telegram_id(77777)


# ── update ─────────────────────────────────────────────────────────────


class TestUserUpdate:
    async def test_update_persists_changes(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user(username="old_name"))
        updated_domain = saved.with_updated_profile(username="new_name")
        result = await repo.update(updated_domain)

        assert result.username == "new_name"

        reloaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert reloaded.username == "new_name"

    async def test_update_deactivation(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        deactivated = saved.deactivate()
        result = await repo.update(deactivated)

        assert result.is_active is False
        reloaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert reloaded.is_active is False

    async def test_update_nonexistent_raises(self, async_session) -> None:
        repo = UserRepository(async_session)
        user = _make_user()
        user = user.model_copy(update={"id": 99999})
        with pytest.raises(NotFoundError):
            await repo.update(user)

    async def test_update_without_id_raises(self, async_session) -> None:
        repo = UserRepository(async_session)
        user = _make_user()  # id=None
        with pytest.raises(NotFoundError, match="without an ID"):
            await repo.update(user)

    async def test_update_returns_domain_model(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        updated = saved.activate()
        result = await repo.update(updated)
        assert isinstance(result, User)


# ── list ───────────────────────────────────────────────────────────────


class TestUserListActive:
    async def test_list_active_returns_only_active(self, async_session) -> None:
        repo = UserRepository(async_session)
        await repo.create(_make_user(telegram_id=1))
        u2 = await repo.create(_make_user(telegram_id=2))
        # deactivate u2
        deactivated = u2.deactivate()
        await repo.update(deactivated)

        active = await repo.list_active()
        assert len(active) == 1
        assert active[0].telegram_id == 1


# ── datetime tz handling ──────────────────────────────────────────────


class TestUserTimezoneHandling:
    async def test_created_at_is_tz_aware(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.created_at.tzinfo is not None

    async def test_updated_at_is_tz_aware(self, async_session) -> None:
        repo = UserRepository(async_session)
        saved = await repo.create(_make_user())
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.updated_at.tzinfo is not None

    async def test_round_trip_preserves_tz(self, async_session) -> None:
        repo = UserRepository(async_session)
        now = datetime.now(UTC)
        user = User(
            telegram_id=555,
            username="tz_test",
            first_name="TZ",
            created_at=now,
            updated_at=now,
        )
        saved = await repo.create(user)
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        # Timestamps should be equal after round-trip (microsecond precision)
        assert abs((loaded.created_at - now).total_seconds()) < 1
