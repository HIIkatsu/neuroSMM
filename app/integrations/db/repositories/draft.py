"""
Draft repository — async SQLAlchemy implementation.

Returns domain :class:`Draft` objects; ORM types never leak to callers.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.draft import Draft
from app.domain.enums import DraftStatus
from app.integrations.db.mappers.draft import draft_to_domain, draft_to_orm
from app.integrations.db.models.draft import DraftORM


class DraftRepository:
    """Async repository for :class:`Draft` persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, draft: Draft) -> Draft:
        """Insert a new draft and return the domain model with an assigned ID."""
        orm = draft_to_orm(draft)
        self._session.add(orm)
        await self._session.flush()
        return draft_to_domain(orm)

    async def get_by_id(self, draft_id: int) -> Draft:
        """Load a draft by its surrogate ID.

        Raises :class:`NotFoundError` if no such draft exists.
        """
        stmt = select(DraftORM).where(DraftORM.id == draft_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise NotFoundError(f"Draft with id={draft_id} not found")
        return draft_to_domain(orm)

    async def list_by_project(
        self,
        project_id: int,
        *,
        status: DraftStatus | None = None,
    ) -> list[Draft]:
        """Return drafts for a project, optionally filtered by status."""
        stmt = select(DraftORM).where(DraftORM.project_id == project_id)
        if status is not None:
            stmt = stmt.where(DraftORM.status == status.value)
        result = await self._session.execute(stmt)
        return [draft_to_domain(orm) for orm in result.scalars().all()]

    async def update(self, draft: Draft) -> Draft:
        """Persist an updated domain draft.

        Raises :class:`NotFoundError` if the draft's ID doesn't exist.
        """
        if draft.id is None:
            raise NotFoundError("Cannot update a draft without an ID")

        stmt = select(DraftORM).where(DraftORM.id == draft.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise NotFoundError(f"Draft with id={draft.id} not found")

        existing.project_id = draft.project_id
        existing.author_id = draft.author_id
        existing.title = draft.title
        existing.text_content = draft.text_content
        existing.image_url = draft.image_url
        existing.content_type = draft.content_type.value
        existing.tone = draft.tone.value
        existing.topic = draft.topic
        existing.status = draft.status.value
        existing.created_at = draft.created_at
        existing.updated_at = draft.updated_at

        await self._session.flush()
        return draft_to_domain(existing)
