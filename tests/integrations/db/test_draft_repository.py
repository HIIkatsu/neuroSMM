"""
Tests for Draft repository — create / load / update / state persistence,
domain-type correctness, and error handling.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import NotFoundError
from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, Platform, Tone
from app.domain.project import Project
from app.domain.user import User
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.db.repositories.user import UserRepository

# ── helpers ────────────────────────────────────────────────────────────


async def _seed_user(session) -> User:
    return await UserRepository(session).create(
        User(telegram_id=200, username="drafter", first_name="Draft")
    )


async def _seed_project(session, owner_id: int) -> Project:
    return await ProjectRepository(session).create(
        Project(owner_id=owner_id, title="Draft Channel", platform=Platform.TELEGRAM)
    )


def _make_draft(project_id: int, author_id: int, **overrides: object) -> Draft:
    defaults: dict[str, object] = {
        "project_id": project_id,
        "author_id": author_id,
        "title": "My Post",
        "text_content": "Hello world",
        "content_type": ContentType.TEXT,
        "tone": Tone.NEUTRAL,
    }
    defaults.update(overrides)
    return Draft(**defaults)  # type: ignore[arg-type]


# ── create ─────────────────────────────────────────────────────────────


class TestDraftCreate:
    async def test_create_assigns_id(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)

        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]
        assert saved.id is not None and saved.id > 0

    async def test_create_preserves_fields(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)

        draft = _make_draft(
            proj.id,  # type: ignore[arg-type]
            user.id,  # type: ignore[arg-type]
            title="Breaking News",
            text_content="Something happened",
            image_url="https://example.com/img.png",
            content_type=ContentType.TEXT_AND_IMAGE,
            tone=Tone.FORMAL,
            topic="news",
        )
        saved = await repo.create(draft)

        assert saved.title == "Breaking News"
        assert saved.text_content == "Something happened"
        assert saved.image_url == "https://example.com/img.png"
        assert saved.content_type == ContentType.TEXT_AND_IMAGE
        assert saved.tone == Tone.FORMAL
        assert saved.topic == "news"
        assert saved.status == DraftStatus.DRAFT

    async def test_create_returns_domain_model(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]
        assert isinstance(saved, Draft)


# ── get by id ──────────────────────────────────────────────────────────


class TestDraftGetById:
    async def test_get_by_id(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.id == saved.id
        assert loaded.title == saved.title

    async def test_get_by_id_not_found(self, async_session) -> None:
        repo = DraftRepository(async_session)
        with pytest.raises(NotFoundError):
            await repo.get_by_id(99999)

    async def test_get_by_id_returns_domain_model(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert isinstance(loaded, Draft)


# ── list by project ───────────────────────────────────────────────────


class TestDraftListByProject:
    async def test_list_by_project(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)

        await repo.create(_make_draft(proj.id, user.id, title="D1"))  # type: ignore[arg-type]
        await repo.create(_make_draft(proj.id, user.id, title="D2"))  # type: ignore[arg-type]

        drafts = await repo.list_by_project(proj.id)  # type: ignore[arg-type]
        assert len(drafts) == 2

    async def test_list_by_project_with_status_filter(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)

        d1 = await repo.create(
            _make_draft(proj.id, user.id, title="D1")  # type: ignore[arg-type]
        )
        await repo.create(
            _make_draft(proj.id, user.id, title="D2")  # type: ignore[arg-type]
        )

        # mark d1 as READY
        ready = d1.mark_ready()
        await repo.update(ready)

        drafts = await repo.list_by_project(
            proj.id, status=DraftStatus.READY  # type: ignore[arg-type]
        )
        assert len(drafts) == 1
        assert drafts[0].status == DraftStatus.READY


# ── update + state persistence ─────────────────────────────────────────


class TestDraftUpdate:
    async def test_update_text_content(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        updated = saved.update_text("Updated text")
        result = await repo.update(updated)
        assert result.text_content == "Updated text"

        reloaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert reloaded.text_content == "Updated text"

    async def test_update_attach_image(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        updated = saved.attach_image("https://example.com/photo.jpg")
        result = await repo.update(updated)
        assert result.image_url == "https://example.com/photo.jpg"

    async def test_state_transition_draft_to_ready(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        ready = saved.mark_ready()
        result = await repo.update(ready)
        assert result.status == DraftStatus.READY

    async def test_state_transition_ready_to_published(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        ready = saved.mark_ready()
        await repo.update(ready)

        published = ready.mark_published()
        result = await repo.update(published)
        assert result.status == DraftStatus.PUBLISHED

    async def test_state_transition_draft_to_archived(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        archived = saved.archive()
        result = await repo.update(archived)
        assert result.status == DraftStatus.ARCHIVED

    async def test_state_persistence_survives_reload(self, async_session) -> None:
        """Verify that state is correctly round-tripped through the DB."""
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]

        ready = saved.mark_ready()
        await repo.update(ready)

        reloaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert reloaded.status == DraftStatus.READY

    async def test_update_nonexistent_raises(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        d = _make_draft(proj.id, user.id)  # type: ignore[arg-type]
        d = d.model_copy(update={"id": 99999})
        with pytest.raises(NotFoundError):
            await repo.update(d)

    async def test_update_without_id_raises(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        d = _make_draft(proj.id, user.id)  # type: ignore[arg-type]
        with pytest.raises(NotFoundError, match="without an ID"):
            await repo.update(d)

    async def test_update_returns_domain_model(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]
        result = await repo.update(saved.update_text("New"))
        assert isinstance(result, Draft)


# ── timezone handling ──────────────────────────────────────────────────


class TestDraftTimezoneHandling:
    async def test_timestamps_are_tz_aware(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        repo = DraftRepository(async_session)
        saved = await repo.create(_make_draft(proj.id, user.id))  # type: ignore[arg-type]
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.created_at.tzinfo is not None
        assert loaded.updated_at.tzinfo is not None
