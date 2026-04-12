"""Scheduler runner — background autopost loop.

:class:`SchedulerRunner` runs an ``asyncio`` loop that periodically queries
for due :class:`ScheduledPost` items and publishes them through the existing
:class:`PublishService` / Telegram publisher pipeline.

Design goals:
- Each poll tick runs in an isolated DB session per scheduled post.
- Execution is idempotent: posts no longer PENDING are skipped silently.
- Failures are persisted to DB state, not silently swallowed.
- The runner exposes ``run_once`` for deterministic testing without ``sleep``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.db.repositories.scheduled_post import ScheduledPostRepository
from app.publishing.provider import Publisher
from app.services.publish import PublishService
from app.services.schedule import ScheduleService

logger = get_logger(__name__)


class SchedulerRunner:
    """Background loop that publishes due scheduled posts automatically.

    Parameters
    ----------
    session_factory:
        Async session factory used to create per-tick DB sessions.
    publisher_factory:
        Zero-argument callable that returns a :class:`Publisher` instance.
        Called once per post execution so publishers remain stateless.
    interval_seconds:
        How often (in seconds) to poll for due posts. Default: 60.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher_factory: Callable[[], Publisher],
        interval_seconds: int = 60,
    ) -> None:
        self._session_factory = session_factory
        self._publisher_factory = publisher_factory
        self._interval = interval_seconds
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    # ── public API ────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the background scheduler loop as an ``asyncio`` task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="scheduler-runner")
        logger.info("Scheduler runner started", extra={"interval_seconds": self._interval})

    async def stop(self) -> None:
        """Stop the background scheduler loop gracefully."""
        self._running = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler runner stopped")

    async def run_once(self) -> int:
        """Execute one poll cycle synchronously.

        Queries for all due PENDING posts and attempts to publish each one.
        Each post is executed in its own DB session/transaction so a failure
        in one post does not affect others.

        Returns
        -------
        int
            Number of posts processed (attempted, not necessarily successful).
        """
        now = datetime.now(UTC)

        # 1. Collect due posts in a short-lived read session
        due_ids: list[int] = []
        async with self._session_factory() as session:
            repo = ScheduledPostRepository(session)
            due_posts = await repo.list_pending(due_before=now)
            due_ids = [p.id for p in due_posts if p.id is not None]

        if not due_ids:
            return 0

        logger.info("Scheduler: %d due post(s) found", len(due_ids))

        # 2. Execute each post in its own session/transaction
        processed = 0
        for schedule_id in due_ids:
            processed += 1
            try:
                await self._execute_post(schedule_id)
            except Exception:
                logger.exception(
                    "Scheduler: unexpected error processing scheduled post %d",
                    schedule_id,
                )

        return processed

    # ── internal ─────────────────────────────────────────────────

    async def _loop(self) -> None:
        """Main async loop — runs until ``_running`` is False."""
        while self._running:
            try:
                await self.run_once()
            except Exception:
                logger.exception("Scheduler: unexpected error in run_once")
            await asyncio.sleep(self._interval)

    async def _execute_post(self, schedule_id: int) -> None:
        """Execute a single scheduled post in an isolated session/transaction."""
        async with self._session_factory() as session:
            try:
                schedule_repo = ScheduledPostRepository(session)
                draft_repo = DraftRepository(session)
                project_repo = ProjectRepository(session)
                publisher = self._publisher_factory()
                publish_svc = PublishService(draft_repo, project_repo, publisher)
                schedule_svc = ScheduleService(
                    schedule_repo, draft_repo, project_repo, publish_svc
                )

                await schedule_svc.execute_scheduled_post(schedule_id)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
