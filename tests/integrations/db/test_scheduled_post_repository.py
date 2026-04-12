"""
Tests for ScheduledPost repository — create / load / update / state persistence,
domain-type correctness, and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import NotFoundError
from app.domain.draft import Draft
from app.domain.enums import ContentType, Platform, ScheduleStatus, Tone
from app.domain.project import Project
from app.domain.schedule import ScheduledPost
from app.domain.user import User
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.db.repositories.scheduled_post import ScheduledPostRepository
from app.integrations.db.repositories.user import UserRepository

# ── helpers ────────────────────────────────────────────────────────────


async def _seed_user(session) -> User:
    return await UserRepository(session).create(
        User(telegram_id=300, username="scheduler", first_name="Sched")
    )


async def _seed_project(session, owner_id: int) -> Project:
    return await ProjectRepository(session).create(
        Project(owner_id=owner_id, title="Sched Channel", platform=Platform.TELEGRAM)
    )


async def _seed_draft(session, project_id: int, author_id: int) -> Draft:
    return await DraftRepository(session).create(
        Draft(
            project_id=project_id,
            author_id=author_id,
            title="Post",
            text_content="Content",
            content_type=ContentType.TEXT,
            tone=Tone.NEUTRAL,
        )
    )


def _make_post(draft_id: int, project_id: int, **overrides: object) -> ScheduledPost:
    defaults: dict[str, object] = {
        "draft_id": draft_id,
        "project_id": project_id,
        "publish_at": datetime.now(UTC) + timedelta(hours=1),
    }
    defaults.update(overrides)
    return ScheduledPost(**defaults)  # type: ignore[arg-type]


# ── create ─────────────────────────────────────────────────────────────


class TestScheduledPostCreate:
    async def test_create_assigns_id(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        assert saved.id is not None and saved.id > 0

    async def test_create_preserves_fields(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        publish_at = datetime.now(UTC) + timedelta(days=7)
        saved = await repo.create(
            _make_post(draft.id, proj.id, publish_at=publish_at)  # type: ignore[arg-type]
        )
        assert saved.status == ScheduleStatus.PENDING
        assert saved.failure_reason is None
        assert saved.published_at is None

    async def test_create_returns_domain_model(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        assert isinstance(saved, ScheduledPost)


# ── get by id ──────────────────────────────────────────────────────────


class TestScheduledPostGetById:
    async def test_get_by_id(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.id == saved.id

    async def test_get_by_id_not_found(self, async_session) -> None:
        repo = ScheduledPostRepository(async_session)
        with pytest.raises(NotFoundError):
            await repo.get_by_id(99999)

    async def test_get_by_id_returns_domain_model(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert isinstance(loaded, ScheduledPost)


# ── list pending ──────────────────────────────────────────────────────


class TestScheduledPostListPending:
    async def test_list_pending(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        pending = await repo.list_pending()
        assert len(pending) == 2

    async def test_list_pending_with_due_before(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        now = datetime.now(UTC)
        soon = now + timedelta(minutes=5)
        later = now + timedelta(days=30)

        await repo.create(
            _make_post(draft.id, proj.id, publish_at=soon)  # type: ignore[arg-type]
        )
        await repo.create(
            _make_post(draft.id, proj.id, publish_at=later)  # type: ignore[arg-type]
        )

        cutoff = now + timedelta(hours=1)
        due = await repo.list_pending(due_before=cutoff)
        assert len(due) == 1

    async def test_list_pending_excludes_non_pending(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        post = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        # Mark as cancelled
        cancelled = post.cancel()
        await repo.update(cancelled)

        pending = await repo.list_pending()
        assert len(pending) == 0


# ── list by project ──────────────────────────────────────────────────


class TestScheduledPostListByProject:
    async def test_list_by_project(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        posts = await repo.list_by_project(proj.id)  # type: ignore[arg-type]
        assert len(posts) == 1


# ── update + state persistence ─────────────────────────────────────────


class TestScheduledPostUpdate:
    async def test_mark_published(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        published = saved.mark_published()
        result = await repo.update(published)
        assert result.status == ScheduleStatus.PUBLISHED
        assert result.published_at is not None

    async def test_mark_failed(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        failed = saved.mark_failed("API timeout")
        result = await repo.update(failed)
        assert result.status == ScheduleStatus.FAILED
        assert result.failure_reason == "API timeout"

    async def test_cancel(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        cancelled = saved.cancel()
        result = await repo.update(cancelled)
        assert result.status == ScheduleStatus.CANCELLED

    async def test_retry_from_failed(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        failed = saved.mark_failed("Network error")
        await repo.update(failed)

        new_time = datetime.now(UTC) + timedelta(hours=2)
        retried = failed.retry(new_time)
        result = await repo.update(retried)
        assert result.status == ScheduleStatus.PENDING
        assert result.failure_reason is None

    async def test_state_persistence_survives_reload(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]

        failed = saved.mark_failed("API error")
        await repo.update(failed)

        reloaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert reloaded.status == ScheduleStatus.FAILED
        assert reloaded.failure_reason == "API error"

    async def test_update_nonexistent_raises(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        post = _make_post(draft.id, proj.id)  # type: ignore[arg-type]
        post = post.model_copy(update={"id": 99999})
        with pytest.raises(NotFoundError):
            await repo.update(post)

    async def test_update_without_id_raises(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        post = _make_post(draft.id, proj.id)  # type: ignore[arg-type]
        with pytest.raises(NotFoundError, match="without an ID"):
            await repo.update(post)

    async def test_update_returns_domain_model(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        result = await repo.update(saved.cancel())
        assert isinstance(result, ScheduledPost)


# ── timezone handling ──────────────────────────────────────────────────


class TestScheduledPostTimezoneHandling:
    async def test_timestamps_are_tz_aware(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)
        saved = await repo.create(_make_post(draft.id, proj.id))  # type: ignore[arg-type]
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]

        assert loaded.created_at.tzinfo is not None
        assert loaded.updated_at.tzinfo is not None
        assert loaded.publish_at.tzinfo is not None

    async def test_publish_at_round_trip(self, async_session) -> None:
        user = await _seed_user(async_session)
        proj = await _seed_project(async_session, user.id)  # type: ignore[arg-type]
        draft = await _seed_draft(async_session, proj.id, user.id)  # type: ignore[arg-type]
        repo = ScheduledPostRepository(async_session)

        target_time = datetime(2027, 6, 15, 14, 30, 0, tzinfo=UTC)
        saved = await repo.create(
            _make_post(
                draft.id, proj.id, publish_at=target_time  # type: ignore[arg-type]
            )
        )
        loaded = await repo.get_by_id(saved.id)  # type: ignore[arg-type]
        assert loaded.publish_at == target_time
