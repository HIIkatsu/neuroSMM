"""Project API routes.

Thin router — all business logic lives in :class:`ProjectService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.domain.user import User
from app.integrations.db.repositories.project import ProjectRepository
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProjectService:
    return ProjectService(ProjectRepository(session))


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectResponse:
    """Create a new project for the current user."""
    assert user.id is not None
    project = await service.create_project(
        owner_id=user.id,
        title=body.title,
        description=body.description,
        platform=body.platform.value,
    )
    return _to_response(project)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List user projects",
)
async def list_projects(
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectListResponse:
    """List all projects belonging to the current user."""
    assert user.id is not None
    projects = await service.list_user_projects(owner_id=user.id)
    items = [_to_response(p) for p in projects]
    return ProjectListResponse(items=items, count=len(items))


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
)
async def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectResponse:
    """Get a project by its ID (ownership enforced)."""
    assert user.id is not None
    project = await service.get_project(project_id=project_id, user_id=user.id)
    return _to_response(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectResponse:
    """Update a project's basic fields (ownership enforced)."""
    assert user.id is not None
    project = await service.update_project(
        project_id=project_id,
        user_id=user.id,
        title=body.title,
        description=body.description,
    )
    return _to_response(project)


@router.post(
    "/{project_id}/deactivate",
    response_model=ProjectResponse,
    summary="Deactivate project",
)
async def deactivate_project(
    project_id: int,
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectResponse:
    """Deactivate a project (soft delete, ownership enforced)."""
    assert user.id is not None
    project = await service.deactivate_project(project_id=project_id, user_id=user.id)
    return _to_response(project)


@router.post(
    "/{project_id}/activate",
    response_model=ProjectResponse,
    summary="Activate project",
)
async def activate_project(
    project_id: int,
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectResponse:
    """Activate a previously deactivated project (ownership enforced)."""
    assert user.id is not None
    project = await service.activate_project(project_id=project_id, user_id=user.id)
    return _to_response(project)


def _to_response(project: object) -> ProjectResponse:
    """Convert a domain Project to a ProjectResponse."""
    from app.domain.project import Project

    assert isinstance(project, Project)
    return ProjectResponse(
        id=project.id,  # type: ignore[arg-type]
        owner_id=project.owner_id,
        title=project.title,
        description=project.description,
        platform=project.platform,
        platform_channel_id=project.platform_channel_id,
        is_active=project.is_active,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
