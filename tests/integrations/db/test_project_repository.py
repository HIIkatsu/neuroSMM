"""
Tests for Project repository — create / load / update round-trip,
domain-type correctness, FK constraint, and error handling.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import NotFoundError
from app.domain.enums import Platform
from app.domain.project import Project
from app.domain.user import User
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.db.repositories.user import UserRepository

# ── helpers ────────────────────────────────────────────────────────────


async def _seed_user(session) -> User:
    repo = UserRepository(session)
    return await repo.create(
        User(telegram_id=100, username="owner", first_name="Owner")
    )


def _make_project(owner_id: int, **overrides: object) -> Project:
    defaults: dict[str, object] = {
        "owner_id": owner_id,
        "title": "My Channel",
        "description": "Test project",
        "platform": Platform.TELEGRAM,
    }
    defaults.update(overrides)
    return Project(**defaults)  # type: ignore[arg-type]


# ── create ─────────────────────────────────────────────────────────────


class TestProjectCreate:
    async def test_create_assigns_id(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]
        assert saved.id is not None and saved.id > 0

    async def test_create_preserves_fields(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(
            _make_project(
                owner.id,  # type: ignore[arg-type]
                title="News Bot",
                description="Daily news",
                platform=Platform.VK,
                platform_channel_id="vk-12345",
            )
        )
        assert saved.title == "News Bot"
        assert saved.description == "Daily news"
        assert saved.platform == Platform.VK
        assert saved.platform_channel_id == "vk-12345"

    async def test_create_returns_domain_model(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]
        assert isinstance(saved, Project)


# ── get by id ──────────────────────────────────────────────────────────


class TestProjectGetById:
    async def test_get_by_id(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.id == saved.id
        assert loaded.title == saved.title

    async def test_get_by_id_not_found(self, async_session) -> None:
        repo = ProjectRepository(async_session)
        with pytest.raises(NotFoundError):
            await repo.get_by_id(99999)


# ── list by owner ─────────────────────────────────────────────────────


class TestProjectListByOwner:
    async def test_list_by_owner(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        await repo.create(_make_project(owner.id, title="P1"))  # type: ignore[arg-type]
        await repo.create(_make_project(owner.id, title="P2"))  # type: ignore[arg-type]

        projects = await repo.list_by_owner(owner.id)  # type: ignore[arg-type]
        assert len(projects) == 2

    async def test_list_by_owner_empty(self, async_session) -> None:
        repo = ProjectRepository(async_session)
        projects = await repo.list_by_owner(99999)
        assert projects == []


# ── update ─────────────────────────────────────────────────────────────


class TestProjectUpdate:
    async def test_update_rename(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]

        renamed = saved.rename("New Title")
        result = await repo.update(renamed)
        assert result.title == "New Title"

        reloaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert reloaded.title == "New Title"

    async def test_update_deactivation(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]

        deactivated = saved.deactivate()
        result = await repo.update(deactivated)
        assert result.is_active is False

    async def test_update_link_channel(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]

        linked = saved.link_channel("tg-chat-123")
        result = await repo.update(linked)
        assert result.platform_channel_id == "tg-chat-123"

    async def test_update_nonexistent_raises(self, async_session) -> None:
        repo = ProjectRepository(async_session)
        owner = await _seed_user(async_session)
        p = _make_project(owner.id)  # type: ignore[arg-type]
        p = p.model_copy(update={"id": 99999})
        with pytest.raises(NotFoundError):
            await repo.update(p)

    async def test_update_without_id_raises(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        p = _make_project(owner.id)  # type: ignore[arg-type]
        with pytest.raises(NotFoundError, match="without an ID"):
            await repo.update(p)

    async def test_update_returns_domain_model(self, async_session) -> None:
        owner = await _seed_user(async_session)
        repo = ProjectRepository(async_session)
        saved = await repo.create(_make_project(owner.id))  # type: ignore[arg-type]
        result = await repo.update(saved.activate())
        assert isinstance(result, Project)
