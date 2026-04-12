"""
Project repository — async SQLAlchemy implementation.

Returns domain :class:`Project` objects; ORM types never leak to callers.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.project import Project
from app.integrations.db.mappers.project import project_to_domain, project_to_orm
from app.integrations.db.models.project import ProjectORM


class ProjectRepository:
    """Async repository for :class:`Project` persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project: Project) -> Project:
        """Insert a new project and return the domain model with an assigned ID."""
        orm = project_to_orm(project)
        self._session.add(orm)
        await self._session.flush()
        return project_to_domain(orm)

    async def get_by_id(self, project_id: int) -> Project:
        """Load a project by its surrogate ID.

        Raises :class:`NotFoundError` if no such project exists.
        """
        stmt = select(ProjectORM).where(ProjectORM.id == project_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise NotFoundError(f"Project with id={project_id} not found")
        return project_to_domain(orm)

    async def list_by_owner(self, owner_id: int) -> list[Project]:
        """Return all projects belonging to a specific user."""
        stmt = select(ProjectORM).where(ProjectORM.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return [project_to_domain(orm) for orm in result.scalars().all()]

    async def update(self, project: Project) -> Project:
        """Persist an updated domain project.

        Raises :class:`NotFoundError` if the project's ID doesn't exist.
        """
        if project.id is None:
            raise NotFoundError("Cannot update a project without an ID")

        stmt = select(ProjectORM).where(ProjectORM.id == project.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise NotFoundError(f"Project with id={project.id} not found")

        existing.owner_id = project.owner_id
        existing.title = project.title
        existing.description = project.description
        existing.platform = project.platform.value
        existing.platform_channel_id = project.platform_channel_id
        existing.is_active = project.is_active
        existing.created_at = project.created_at
        existing.updated_at = project.updated_at

        await self._session.flush()
        return project_to_domain(existing)
