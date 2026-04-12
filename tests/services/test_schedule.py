"""Tests for ScheduleService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, ValidationError
from app.domain.draft import Draft
from app.domain.enums import ContentType, DraftStatus, ScheduleStatus, Tone
from app.domain.project import Project
from app.domain.schedule import ScheduledPost
from app.publishing.provider import PublishResult
from app.services.publish import PublishService
from app.services.schedule import ScheduleService

# ── helpers ──────────────────────────────────────────────────────────


def _future(seconds: int = 3600) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


def _past(seconds: int = 3600) -> datetime:
    return datetime.now(UTC) - timedelta(seconds=seconds)


def _make_project(*, owner_id: int = 1, project_id: int = 1) -> Project:
    return Project(id=project_id, owner_id=owner_id, title="Project")


def _make_draft(
    *,
    draft_id: int = 10,
    project_id: int = 1,
    author_id: int = 1,
    status: DraftStatus = DraftStatus.READY,
    text_content: str = "Post content",
) -> Draft:
    return Draft(
        id=draft_id,
        project_id=project_id,
        author_id=author_id,
        status=status,
        title="My Draft",
        text_content=text_content,
        content_type=ContentType.TEXT,
        tone=Tone.NEUTRAL,
    )


def _make_schedule(
    *,
    schedule_id: int = 1,
    draft_id: int = 10,
    project_id: int = 1,
    status: ScheduleStatus = ScheduleStatus.PENDING,
    publish_at: datetime | None = None,
    failure_reason: str | None = None,
) -> ScheduledPost:
    return ScheduledPost(
        id=schedule_id,
        draft_id=draft_id,
        project_id=project_id,
        publish_at=publish_at or _future(),
        status=status,
        failure_reason=failure_reason,
    )


def _build_service(
    *,
    schedule: ScheduledPost | None = None,
    draft: Draft | None = None,
    project: Project | None = None,
    publish_result: PublishResult | None = None,
    schedules: list[ScheduledPost] | None = None,
) -> ScheduleService:
    schedule_repo = AsyncMock()
    draft_repo = AsyncMock()
    project_repo = AsyncMock()
    publisher = AsyncMock()

    if schedule is not None:
        schedule_repo.get_by_id.return_value = schedule
        schedule_repo.update.side_effect = lambda s: s

    if draft is not None:
        draft_repo.get_by_id.return_value = draft
        draft_repo.update.side_effect = lambda d: d

    if project is not None:
        project_repo.get_by_id.return_value = project

    if publish_result is not None:
        publisher.publish.return_value = publish_result

    if schedules is not None:
        schedule_repo.list_by_project.return_value = schedules
        schedule_repo.create.side_effect = lambda s: s

    publish_svc = PublishService(draft_repo, project_repo, publisher)
    return ScheduleService(schedule_repo, draft_repo, project_repo, publish_svc)


# ── create_schedule tests ─────────────────────────────────────────────


class TestCreateSchedule:
    async def test_create_schedule_valid(self) -> None:
        """Create schedule for a READY draft succeeds."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.READY)
        service = _build_service(project=project, draft=draft)
        service._schedule_repo.create.side_effect = lambda s: ScheduledPost(
            id=42,
            draft_id=s.draft_id,
            project_id=s.project_id,
            publish_at=s.publish_at,
        )

        post = await service.create_schedule(
            draft_id=10,
            project_id=1,
            publish_at=_future(),
            user_id=1,
        )

        assert post.draft_id == 10
        assert post.project_id == 1
        assert post.status == ScheduleStatus.PENDING

    async def test_create_schedule_draft_status_not_ready_rejected(self) -> None:
        """Cannot schedule a draft that is not in READY status."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.DRAFT)
        service = _build_service(project=project, draft=draft)

        with pytest.raises(ConflictError, match="ready"):
            await service.create_schedule(
                draft_id=10,
                project_id=1,
                publish_at=_future(),
                user_id=1,
            )

    async def test_create_schedule_archived_draft_rejected(self) -> None:
        """Cannot schedule an archived draft."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.ARCHIVED)
        service = _build_service(project=project, draft=draft)

        with pytest.raises(ConflictError, match="ready"):
            await service.create_schedule(
                draft_id=10,
                project_id=1,
                publish_at=_future(),
                user_id=1,
            )

    async def test_create_schedule_published_draft_rejected(self) -> None:
        """Cannot schedule an already published draft."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.PUBLISHED)
        service = _build_service(project=project, draft=draft)

        with pytest.raises(ConflictError, match="ready"):
            await service.create_schedule(
                draft_id=10,
                project_id=1,
                publish_at=_future(),
                user_id=1,
            )

    async def test_create_schedule_publish_at_in_past_rejected(self) -> None:
        """Cannot schedule with a past publish_at timestamp."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.READY)
        service = _build_service(project=project, draft=draft)

        with pytest.raises(ValidationError, match="future"):
            await service.create_schedule(
                draft_id=10,
                project_id=1,
                publish_at=_past(),
                user_id=1,
            )

    async def test_create_schedule_unauthorized_user_rejected(self) -> None:
        """Create schedule is denied when user does not own the project."""
        project = _make_project(owner_id=99)
        draft = _make_draft(status=DraftStatus.READY)
        service = _build_service(project=project, draft=draft)

        with pytest.raises(AuthorizationError):
            await service.create_schedule(
                draft_id=10,
                project_id=1,
                publish_at=_future(),
                user_id=1,
            )

    async def test_create_schedule_draft_wrong_project_rejected(self) -> None:
        """Create schedule is denied when draft does not belong to the project."""
        project = _make_project(project_id=1)
        draft = _make_draft(project_id=2)  # different project
        service = _build_service(project=project, draft=draft)

        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await service.create_schedule(
                draft_id=10,
                project_id=1,
                publish_at=_future(),
                user_id=1,
            )


# ── cancel_schedule tests ─────────────────────────────────────────────


class TestCancelSchedule:
    async def test_cancel_pending_schedule_succeeds(self) -> None:
        """Cancel a PENDING schedule transitions to CANCELLED."""
        project = _make_project()
        schedule = _make_schedule(status=ScheduleStatus.PENDING)
        service = _build_service(project=project, schedule=schedule)

        result = await service.cancel_schedule(schedule_id=1, user_id=1)

        assert result.status == ScheduleStatus.CANCELLED

    async def test_cancel_published_schedule_rejected(self) -> None:
        """Cannot cancel a PUBLISHED schedule."""
        project = _make_project()
        schedule = _make_schedule(status=ScheduleStatus.PUBLISHED)
        service = _build_service(project=project, schedule=schedule)

        with pytest.raises(ConflictError):
            await service.cancel_schedule(schedule_id=1, user_id=1)

    async def test_cancel_unauthorized_user_rejected(self) -> None:
        """Cancel is denied when user does not own the project."""
        project = _make_project(owner_id=99)
        schedule = _make_schedule(status=ScheduleStatus.PENDING)
        service = _build_service(project=project, schedule=schedule)

        with pytest.raises(AuthorizationError):
            await service.cancel_schedule(schedule_id=1, user_id=1)


# ── retry_schedule tests ──────────────────────────────────────────────


class TestRetrySchedule:
    async def test_retry_failed_schedule_succeeds(self) -> None:
        """Retry a FAILED schedule with a new future time."""
        project = _make_project()
        schedule = _make_schedule(
            status=ScheduleStatus.FAILED, failure_reason="Network error"
        )
        service = _build_service(project=project, schedule=schedule)
        new_time = _future(7200)

        result = await service.retry_schedule(
            schedule_id=1, user_id=1, new_publish_at=new_time
        )

        assert result.status == ScheduleStatus.PENDING
        assert result.publish_at == new_time
        assert result.failure_reason is None

    async def test_retry_pending_schedule_rejected(self) -> None:
        """Cannot retry a schedule that is not FAILED."""
        project = _make_project()
        schedule = _make_schedule(status=ScheduleStatus.PENDING)
        service = _build_service(project=project, schedule=schedule)

        with pytest.raises(ConflictError, match="failed"):
            await service.retry_schedule(
                schedule_id=1, user_id=1, new_publish_at=_future()
            )

    async def test_retry_with_past_time_rejected(self) -> None:
        """Retry with a past new_publish_at is rejected."""
        project = _make_project()
        schedule = _make_schedule(status=ScheduleStatus.FAILED, failure_reason="err")
        service = _build_service(project=project, schedule=schedule)

        with pytest.raises(ValidationError, match="future"):
            await service.retry_schedule(
                schedule_id=1, user_id=1, new_publish_at=_past()
            )

    async def test_retry_unauthorized_user_rejected(self) -> None:
        """Retry is denied when user does not own the project."""
        project = _make_project(owner_id=99)
        schedule = _make_schedule(status=ScheduleStatus.FAILED, failure_reason="err")
        service = _build_service(project=project, schedule=schedule)

        with pytest.raises(AuthorizationError):
            await service.retry_schedule(
                schedule_id=1, user_id=1, new_publish_at=_future()
            )


# ── list_by_project tests ─────────────────────────────────────────────


class TestListByProject:
    async def test_list_returns_all_project_schedules(self) -> None:
        """List returns all schedules for the project."""
        project = _make_project()
        schedules = [
            _make_schedule(schedule_id=1),
            _make_schedule(schedule_id=2, status=ScheduleStatus.PUBLISHED),
        ]
        service = _build_service(project=project, schedules=schedules)

        result = await service.list_by_project(project_id=1, user_id=1)

        assert len(result) == 2

    async def test_list_unauthorized_user_rejected(self) -> None:
        """List is denied when user does not own the project."""
        project = _make_project(owner_id=99)
        service = _build_service(project=project, schedules=[])

        with pytest.raises(AuthorizationError):
            await service.list_by_project(project_id=1, user_id=1)


# ── execute_scheduled_post tests ──────────────────────────────────────


class TestExecuteScheduledPost:
    async def test_successful_execution_marks_published(self) -> None:
        """Successful publish transitions schedule to PUBLISHED."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.READY)
        schedule = _make_schedule(
            status=ScheduleStatus.PENDING,
            publish_at=_past(60),  # already due
        )
        result = PublishResult(success=True, platform_post_id="tg-1")
        service = _build_service(
            project=project, draft=draft, schedule=schedule, publish_result=result
        )

        await service.execute_scheduled_post(1)

        service._schedule_repo.update.assert_called_once()
        saved = service._schedule_repo.update.call_args.args[0]
        assert saved.status == ScheduleStatus.PUBLISHED

    async def test_failed_publish_marks_failed_with_reason(self) -> None:
        """Failed publish transitions schedule to FAILED with a reason."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.READY)
        schedule = _make_schedule(status=ScheduleStatus.PENDING, publish_at=_past(60))
        result = PublishResult(success=False, error_message="Bot blocked by user")
        service = _build_service(
            project=project, draft=draft, schedule=schedule, publish_result=result
        )

        await service.execute_scheduled_post(1)

        saved = service._schedule_repo.update.call_args.args[0]
        assert saved.status == ScheduleStatus.FAILED
        assert "blocked" in saved.failure_reason

    async def test_non_ready_draft_marks_failed(self) -> None:
        """If draft is not READY, execution records failure without raising."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.DRAFT)
        schedule = _make_schedule(status=ScheduleStatus.PENDING, publish_at=_past(60))
        result = PublishResult(success=True)
        service = _build_service(
            project=project, draft=draft, schedule=schedule, publish_result=result
        )

        # Should not raise — failure is persisted
        await service.execute_scheduled_post(1)

        saved = service._schedule_repo.update.call_args.args[0]
        assert saved.status == ScheduleStatus.FAILED

    async def test_non_pending_schedule_is_skipped(self) -> None:
        """A PUBLISHED or CANCELLED schedule is skipped silently (idempotent)."""
        project = _make_project()
        draft = _make_draft(status=DraftStatus.READY)
        schedule = _make_schedule(status=ScheduleStatus.PUBLISHED)
        service = _build_service(project=project, draft=draft, schedule=schedule)

        await service.execute_scheduled_post(1)

        # update should not be called — nothing changed
        service._schedule_repo.update.assert_not_called()

    async def test_cancelled_schedule_is_skipped(self) -> None:
        """A CANCELLED schedule is skipped silently (idempotent)."""
        project = _make_project()
        schedule = _make_schedule(status=ScheduleStatus.CANCELLED)
        service = _build_service(project=project, schedule=schedule)

        await service.execute_scheduled_post(1)

        service._schedule_repo.update.assert_not_called()

    async def test_failed_schedule_is_skipped_without_retry(self) -> None:
        """A FAILED schedule (awaiting retry) is skipped silently."""
        project = _make_project()
        schedule = _make_schedule(
            status=ScheduleStatus.FAILED, failure_reason="previous error"
        )
        service = _build_service(project=project, schedule=schedule)

        await service.execute_scheduled_post(1)

        service._schedule_repo.update.assert_not_called()
