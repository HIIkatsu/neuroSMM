"""
ScheduledPost repository — async SQLAlchemy implementation.

Returns domain :class:`ScheduledPost` objects; ORM types never leak to callers.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.enums import ScheduleStatus
from app.domain.schedule import ScheduledPost
from app.integrations.db.mappers.scheduled_post import (
    scheduled_post_to_domain,
    scheduled_post_to_orm,
)
from app.integrations.db.models.scheduled_post import ScheduledPostORM


class ScheduledPostRepository:
    """Async repository for :class:`ScheduledPost` persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, post: ScheduledPost) -> ScheduledPost:
        """Insert a new scheduled post and return the domain model with an assigned ID."""
        orm = scheduled_post_to_orm(post)
        self._session.add(orm)
        await self._session.flush()
        return scheduled_post_to_domain(orm)

    async def get_by_id(self, post_id: int) -> ScheduledPost:
        """Load a scheduled post by its surrogate ID.

        Raises :class:`NotFoundError` if no such post exists.
        """
        stmt = select(ScheduledPostORM).where(ScheduledPostORM.id == post_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise NotFoundError(f"ScheduledPost with id={post_id} not found")
        return scheduled_post_to_domain(orm)

    async def list_pending(
        self,
        *,
        due_before: datetime | None = None,
    ) -> list[ScheduledPost]:
        """Return all pending scheduled posts, optionally due before a timestamp."""
        stmt = select(ScheduledPostORM).where(
            ScheduledPostORM.status == ScheduleStatus.PENDING.value
        )
        if due_before is not None:
            stmt = stmt.where(ScheduledPostORM.publish_at <= due_before)
        result = await self._session.execute(stmt)
        return [scheduled_post_to_domain(orm) for orm in result.scalars().all()]

    async def list_by_project(self, project_id: int) -> list[ScheduledPost]:
        """Return all scheduled posts for a project."""
        stmt = select(ScheduledPostORM).where(
            ScheduledPostORM.project_id == project_id
        )
        result = await self._session.execute(stmt)
        return [scheduled_post_to_domain(orm) for orm in result.scalars().all()]

    async def update(self, post: ScheduledPost) -> ScheduledPost:
        """Persist an updated domain scheduled post.

        Raises :class:`NotFoundError` if the post's ID doesn't exist.
        """
        if post.id is None:
            raise NotFoundError("Cannot update a scheduled post without an ID")

        stmt = select(ScheduledPostORM).where(ScheduledPostORM.id == post.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise NotFoundError(f"ScheduledPost with id={post.id} not found")

        existing.draft_id = post.draft_id
        existing.project_id = post.project_id
        existing.publish_at = post.publish_at
        existing.status = post.status.value
        existing.failure_reason = post.failure_reason
        existing.published_at = post.published_at
        existing.created_at = post.created_at
        existing.updated_at = post.updated_at

        await self._session.flush()
        return scheduled_post_to_domain(existing)
