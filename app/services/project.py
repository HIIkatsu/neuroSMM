"""Project service — business logic for project use cases.

Operates on domain models, enforces ownership, delegates to repository.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import AuthorizationError
from app.domain.project import Project
from app.integrations.db.repositories.project import ProjectRepository


class ProjectService:
    """Service for project-related operations."""

    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def create_project(
        self,
        *,
        owner_id: int,
        title: str,
        description: str = "",
        platform: str = "telegram",
    ) -> Project:
        """Create a new project for the given owner."""
        from app.domain.enums import Platform

        project = Project(
            owner_id=owner_id,
            title=title,
            description=description,
            platform=Platform(platform),
        )
        return await self._repo.create(project)

    async def get_project(self, *, project_id: int, user_id: int) -> Project:
        """Get a project by ID, enforcing ownership.

        Raises
        ------
        NotFoundError
            If the project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        project = await self._repo.get_by_id(project_id)
        self._check_ownership(project, user_id)
        return project

    async def list_user_projects(self, *, owner_id: int) -> list[Project]:
        """List all projects belonging to a user."""
        return await self._repo.list_by_owner(owner_id)

    async def update_project(
        self,
        *,
        project_id: int,
        user_id: int,
        title: str | None = None,
        description: str | None = None,
    ) -> Project:
        """Update a project's basic fields, enforcing ownership.

        Raises
        ------
        NotFoundError
            If the project does not exist.
        AuthorizationError
            If the user does not own the project.
        """
        project = await self._repo.get_by_id(project_id)
        self._check_ownership(project, user_id)

        updates: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if title is not None:
            updates["title"] = title.strip()
        if description is not None:
            updates["description"] = description.strip()

        updated = project.model_copy(update=updates)
        return await self._repo.update(updated)

    async def deactivate_project(self, *, project_id: int, user_id: int) -> Project:
        """Deactivate a project, enforcing ownership."""
        project = await self._repo.get_by_id(project_id)
        self._check_ownership(project, user_id)
        deactivated = project.deactivate()
        return await self._repo.update(deactivated)

    async def activate_project(self, *, project_id: int, user_id: int) -> Project:
        """Activate a project, enforcing ownership."""
        project = await self._repo.get_by_id(project_id)
        self._check_ownership(project, user_id)
        activated = project.activate()
        return await self._repo.update(activated)

    @staticmethod
    def _check_ownership(project: Project, user_id: int) -> None:
        """Raise AuthorizationError if the user does not own the project."""
        if project.owner_id != user_id:
            raise AuthorizationError("У вас нет доступа к этому проекту")
