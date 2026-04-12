"""Tests for SchedulerRunner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.enums import ScheduleStatus
from app.domain.schedule import ScheduledPost
from app.scheduler.runner import SchedulerRunner

# ── helpers ──────────────────────────────────────────────────────────


def _future(seconds: int = 3600) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


def _past(seconds: int = 60) -> datetime:
    return datetime.now(UTC) - timedelta(seconds=seconds)


def _make_schedule(
    schedule_id: int = 1,
    *,
    status: ScheduleStatus = ScheduleStatus.PENDING,
    publish_at: datetime | None = None,
) -> ScheduledPost:
    return ScheduledPost(
        id=schedule_id,
        draft_id=10,
        project_id=1,
        publish_at=publish_at or _past(),
        status=status,
    )


def _make_runner(
    *,
    session_factory: MagicMock | None = None,
    interval: int = 60,
) -> tuple[SchedulerRunner, MagicMock]:
    """Return a runner with a mock session factory and publisher factory."""
    if session_factory is None:
        session_factory = MagicMock()

    publisher_factory = MagicMock()
    runner = SchedulerRunner(
        session_factory=session_factory,
        publisher_factory=publisher_factory,
        interval_seconds=interval,
    )
    return runner, publisher_factory


# ── run_once tests ────────────────────────────────────────────────────


class TestRunOnce:
    async def test_run_once_no_due_posts_returns_zero(self) -> None:
        """run_once returns 0 when there are no due posts."""
        # Patch the ScheduleService.execute_scheduled_post and repo
        session_factory = MagicMock()
        mock_session = AsyncMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        runner, _ = _make_runner(session_factory=session_factory)

        with patch(
            "app.scheduler.runner.ScheduledPostRepository"
        ) as MockRepo:
            mock_repo = AsyncMock()
            mock_repo.list_pending.return_value = []
            MockRepo.return_value = mock_repo

            count = await runner.run_once()

        assert count == 0

    async def test_run_once_executes_due_posts(self) -> None:
        """run_once processes each due post via _execute_post."""
        runner, _ = _make_runner()

        due_posts = [_make_schedule(1), _make_schedule(2)]

        with (
            patch.object(runner, "_execute_post", new_callable=AsyncMock) as mock_exec,
            patch(
                "app.scheduler.runner.ScheduledPostRepository"
            ) as MockRepo,
        ):
            mock_session = AsyncMock()

            async def _session_ctx():
                return mock_session

            # Make session_factory context manager work
            runner._session_factory = MagicMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            runner._session_factory.return_value = mock_ctx

            mock_repo = AsyncMock()
            mock_repo.list_pending.return_value = due_posts
            MockRepo.return_value = mock_repo

            count = await runner.run_once()

        assert count == 2
        assert mock_exec.call_count == 2
        mock_exec.assert_any_call(1)
        mock_exec.assert_any_call(2)

    async def test_run_once_continues_after_post_failure(self) -> None:
        """run_once continues processing remaining posts even if one fails."""
        runner, _ = _make_runner()
        due_posts = [_make_schedule(1), _make_schedule(2), _make_schedule(3)]
        executed: list[int] = []

        async def _failing_exec(schedule_id: int) -> None:
            if schedule_id == 2:
                raise RuntimeError("unexpected failure")
            executed.append(schedule_id)

        with (
            patch.object(runner, "_execute_post", side_effect=_failing_exec),
            patch("app.scheduler.runner.ScheduledPostRepository") as MockRepo,
        ):
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            runner._session_factory = MagicMock(return_value=mock_ctx)

            mock_repo = AsyncMock()
            mock_repo.list_pending.return_value = due_posts
            MockRepo.return_value = mock_repo

            count = await runner.run_once()

        # 3 attempted (2 succeeded, 1 failed) — count is processed attempts
        assert count == 3
        # Posts 1 and 3 were executed successfully
        assert 1 in executed
        assert 3 in executed
        assert 2 not in executed

    async def test_run_once_skips_posts_without_id(self) -> None:
        """run_once skips any post whose id is None."""
        runner, _ = _make_runner()
        # Post with id=None (shouldn't happen in normal flow but defensive)
        post_no_id = ScheduledPost(
            id=None,
            draft_id=10,
            project_id=1,
            publish_at=_past(),
        )
        due_posts = [post_no_id]

        with (
            patch.object(runner, "_execute_post", new_callable=AsyncMock) as mock_exec,
            patch("app.scheduler.runner.ScheduledPostRepository") as MockRepo,
        ):
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            runner._session_factory = MagicMock(return_value=mock_ctx)

            mock_repo = AsyncMock()
            mock_repo.list_pending.return_value = due_posts
            MockRepo.return_value = mock_repo

            count = await runner.run_once()

        assert count == 0
        mock_exec.assert_not_called()


# ── start / stop tests ────────────────────────────────────────────────


class TestStartStop:
    async def test_start_and_stop(self) -> None:
        """Runner starts a background task and stops it cleanly."""
        runner, _ = _make_runner(interval=1000)

        with patch.object(runner, "run_once", new_callable=AsyncMock):
            await runner.start()
            assert runner._running is True
            assert runner._task is not None
            assert not runner._task.done()

            await runner.stop()
            assert runner._running is False

    async def test_start_is_idempotent(self) -> None:
        """Calling start() a second time is a no-op."""
        runner, _ = _make_runner(interval=1000)

        with patch.object(runner, "run_once", new_callable=AsyncMock):
            await runner.start()
            first_task = runner._task

            await runner.start()
            assert runner._task is first_task  # same task

            await runner.stop()

    async def test_stop_before_start_is_safe(self) -> None:
        """Calling stop() before start() does not raise."""
        runner, _ = _make_runner()
        await runner.stop()  # should not raise
