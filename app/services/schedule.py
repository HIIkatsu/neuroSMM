"""Scheduling orchestration service.

Provides all business logic for scheduled post lifecycle:
- Creating a new schedule for a READY draft
- Cancelling a pending schedule
- Retrying a failed schedule with a new publish time
- Listing schedules for a project
- Executing a due scheduled post via the existing publish flow

No scheduling runtime logic lives here — that belongs in app.scheduler.runner.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.exceptions import AuthorizationError, NotFoundError
from app.domain.enums import DraftStatus, ScheduleStatus
from app.domain.schedule import ScheduledPost
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.db.repositories.scheduled_post import ScheduledPostRepository
from app.services.publish import PublishService

logger = logging.getLogger(__name__)


class ScheduleService:
    """Orchestrates the full lifecycle of a :class:`ScheduledPost`.

    Responsibilities:
    - Validate draft state and ownership when creating a schedule
    - Enforce ownership when cancelling or retrying
    - Delegate publish execution to :class:`PublishService`
    - Persist state transitions (PUBLISHED / FAILED) after execution
    """

    def __init__(
        self,
        schedule_repo: ScheduledPostRepository,
        draft_repo: DraftRepository,
        project_repo: ProjectRepository,
        publish_service: PublishService,
    ) -> None:
        self._schedule_repo = schedule_repo
        self._draft_repo = draft_repo
        self._project_repo = project_repo
        self._publish_service = publish_service

    # ── schedule creation ─────────────────────────────────────────

    async def create_schedule(
        self,
        *,
        draft_id: int,
        project_id: int,
        publish_at: datetime,
        user_id: int,
    ) -> ScheduledPost:
        """Create a new scheduled post for a READY draft.

        Parameters
        ----------
        draft_id:
            ID of the draft to schedule.
        project_id:
            ID of the project that owns the draft.
        publish_at:
            UTC datetime for the scheduled publication.
        user_id:
            ID of the requesting user (ownership check).

        Returns
        -------
        ScheduledPost
            The persisted scheduled post in PENDING status.

        Raises
        ------
        NotFoundError
            If the draft or project does not exist.
        AuthorizationError
            If the user does not own the project.
        ConflictError
            If the draft is not in READY status.
        ValidationError
            If ``publish_at`` is not in the future or lacks timezone info.
        """
        # 1. Verify project ownership
        project = await self._project_repo.get_by_id(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError("У вас нет доступа к этому проекту")

        # 2. Verify draft belongs to this project
        draft = await self._draft_repo.get_by_id(draft_id)
        if draft.project_id != project_id:
            raise NotFoundError(f"Draft {draft_id} does not belong to project {project_id}")

        # 3. Enforce READY state (must be publishable)
        from app.core.exceptions import ConflictError

        if draft.status != DraftStatus.READY:
            raise ConflictError(
                "Черновик должен быть в статусе 'ready' для планирования,"
                f" текущий статус: '{draft.status}'"
            )

        # 4. Build domain object (validates publish_at timezone + future check)
        post = ScheduledPost(
            draft_id=draft_id,
            project_id=project_id,
            publish_at=publish_at,
        )
        post.validate_publish_time()

        return await self._schedule_repo.create(post)

    # ── cancel ────────────────────────────────────────────────────

    async def cancel_schedule(
        self,
        *,
        schedule_id: int,
        user_id: int,
    ) -> ScheduledPost:
        """Cancel a pending scheduled post.

        Raises
        ------
        NotFoundError
            If no scheduled post with ``schedule_id`` exists.
        AuthorizationError
            If the user does not own the project.
        ConflictError
            If the schedule is not in a cancellable state.
        """
        schedule = await self._schedule_repo.get_by_id(schedule_id)
        await self._assert_ownership(schedule.project_id, user_id)
        cancelled = schedule.cancel()
        return await self._schedule_repo.update(cancelled)

    # ── retry ─────────────────────────────────────────────────────

    async def retry_schedule(
        self,
        *,
        schedule_id: int,
        user_id: int,
        new_publish_at: datetime,
    ) -> ScheduledPost:
        """Re-schedule a failed post for a new time.

        Raises
        ------
        NotFoundError
            If the schedule does not exist.
        AuthorizationError
            If the user does not own the project.
        ConflictError
            If the schedule is not in FAILED status.
        ValidationError
            If ``new_publish_at`` is not in the future or lacks timezone info.
        """
        schedule = await self._schedule_repo.get_by_id(schedule_id)
        await self._assert_ownership(schedule.project_id, user_id)
        retried = schedule.retry(new_publish_at)
        retried.validate_publish_time()
        return await self._schedule_repo.update(retried)

    # ── list ──────────────────────────────────────────────────────

    async def list_by_project(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> list[ScheduledPost]:
        """Return all scheduled posts for a project.

        Raises
        ------
        AuthorizationError
            If the user does not own the project.
        """
        await self._assert_ownership(project_id, user_id)
        return await self._schedule_repo.list_by_project(project_id)

    # ── execution (called by scheduler runner) ────────────────────

    async def execute_scheduled_post(self, schedule_id: int) -> None:
        """Execute a single due scheduled post through the publish flow.

        This method is idempotent: if the schedule is no longer PENDING when
        called, it returns immediately without any side effects.

        On success the schedule is transitioned to PUBLISHED and the draft to
        PUBLISHED (via :class:`PublishService`).
        On failure the schedule is transitioned to FAILED with a recorded
        reason; the exception is not re-raised so the caller (scheduler runner)
        can continue processing other posts.

        Parameters
        ----------
        schedule_id:
            Surrogate ID of the :class:`ScheduledPost` to execute.
        """
        schedule = await self._schedule_repo.get_by_id(schedule_id)

        # Idempotency guard: skip if no longer pending
        if schedule.status != ScheduleStatus.PENDING:
            logger.debug(
                "Skipping scheduled post %d — status is %s",
                schedule_id,
                schedule.status,
            )
            return

        project = await self._project_repo.get_by_id(schedule.project_id)
        owner_id = project.owner_id

        try:
            await self._publish_service.publish_draft(
                draft_id=schedule.draft_id,
                user_id=owner_id,
            )
            updated = schedule.mark_published()
            logger.info(
                "Scheduled post %d published successfully",
                schedule_id,
                extra={"draft_id": schedule.draft_id, "project_id": schedule.project_id},
            )
        except Exception as exc:
            msg = getattr(exc, "message", None)
            if not msg:
                msg = str(exc) if str(exc) else type(exc).__name__
            reason = msg
            updated = schedule.mark_failed(reason)
            logger.error(
                "Scheduled post %d failed: %s",
                schedule_id,
                reason,
                extra={"draft_id": schedule.draft_id, "project_id": schedule.project_id},
            )

        await self._schedule_repo.update(updated)

    # ── helpers ───────────────────────────────────────────────────

    async def _assert_ownership(self, project_id: int, user_id: int) -> None:
        """Raise :class:`AuthorizationError` if user does not own the project."""
        project = await self._project_repo.get_by_id(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError("У вас нет доступа к этому проекту")


# ── factory helper ────────────────────────────────────────────────────


def build_schedule_service(
    session: object,
    publisher: object,
) -> ScheduleService:
    """Construct a :class:`ScheduleService` from an async DB session and a publisher.

    Shared by the API route dependency and the scheduler runner to avoid
    duplicating the service-wiring boilerplate in both places.

    Parameters
    ----------
    session:
        An ``AsyncSession`` instance.
    publisher:
        A :class:`~app.publishing.provider.Publisher` implementation.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)

    draft_repo = DraftRepository(session)
    project_repo = ProjectRepository(session)
    schedule_repo = ScheduledPostRepository(session)
    publish_svc = PublishService(draft_repo, project_repo, publisher)  # type: ignore[arg-type]
    return ScheduleService(schedule_repo, draft_repo, project_repo, publish_svc)
