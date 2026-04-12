"""Draft API routes.

Thin router — all business logic lives in :class:`DraftService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.draft import (
    DraftCreate,
    DraftListResponse,
    DraftResponse,
    DraftUpdate,
)
from app.domain.draft import Draft
from app.domain.user import User
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.services.draft import DraftService

router = APIRouter(prefix="/projects/{project_id}/drafts", tags=["drafts"])


def _get_draft_service(
    session: AsyncSession = Depends(get_db_session),
) -> DraftService:
    return DraftService(DraftRepository(session), ProjectRepository(session))


@router.post(
    "",
    response_model=DraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft",
)
async def create_draft(
    project_id: int,
    body: DraftCreate,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftResponse:
    """Create a new draft inside a project (project ownership enforced)."""
    assert user.id is not None
    draft = await service.create_draft(
        project_id=project_id,
        author_id=user.id,
        title=body.title,
        text_content=body.text_content,
        content_type=body.content_type.value,
        tone=body.tone.value,
        topic=body.topic,
    )
    return _to_response(draft)


@router.get(
    "",
    response_model=DraftListResponse,
    summary="List drafts for project",
)
async def list_drafts(
    project_id: int,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftListResponse:
    """List all drafts in a project (project ownership enforced)."""
    assert user.id is not None
    drafts = await service.list_drafts(project_id=project_id, user_id=user.id)
    items = [_to_response(d) for d in drafts]
    return DraftListResponse(items=items, count=len(items))


@router.get(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Get draft by ID",
)
async def get_draft(
    project_id: int,
    draft_id: int,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftResponse:
    """Get a specific draft (project ownership enforced)."""
    assert user.id is not None
    draft = await service.get_draft(draft_id=draft_id, user_id=user.id)
    return _to_response(draft)


@router.patch(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Update draft",
)
async def update_draft(
    project_id: int,
    draft_id: int,
    body: DraftUpdate,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftResponse:
    """Update a draft's text, title, or topic (project ownership enforced)."""
    assert user.id is not None
    draft = await service.update_draft(
        draft_id=draft_id,
        user_id=user.id,
        title=body.title,
        text_content=body.text_content,
        topic=body.topic,
    )
    return _to_response(draft)


@router.post(
    "/{draft_id}/ready",
    response_model=DraftResponse,
    summary="Mark draft as ready",
)
async def mark_ready(
    project_id: int,
    draft_id: int,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftResponse:
    """Transition a draft to READY status (project ownership enforced)."""
    assert user.id is not None
    draft = await service.mark_ready(draft_id=draft_id, user_id=user.id)
    return _to_response(draft)


@router.post(
    "/{draft_id}/back-to-draft",
    response_model=DraftResponse,
    summary="Send back to draft",
)
async def send_back_to_draft(
    project_id: int,
    draft_id: int,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftResponse:
    """Send a READY draft back to DRAFT status (project ownership enforced)."""
    assert user.id is not None
    draft = await service.send_back_to_draft(draft_id=draft_id, user_id=user.id)
    return _to_response(draft)


@router.post(
    "/{draft_id}/archive",
    response_model=DraftResponse,
    summary="Archive draft",
)
async def archive_draft(
    project_id: int,
    draft_id: int,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(_get_draft_service),
) -> DraftResponse:
    """Archive a draft (project ownership enforced)."""
    assert user.id is not None
    draft = await service.archive_draft(draft_id=draft_id, user_id=user.id)
    return _to_response(draft)


def _to_response(draft: Draft) -> DraftResponse:
    """Convert a domain Draft to a DraftResponse."""
    return DraftResponse(
        id=draft.id,  # type: ignore[arg-type]
        project_id=draft.project_id,
        author_id=draft.author_id,
        title=draft.title,
        text_content=draft.text_content,
        image_url=draft.image_url,
        content_type=draft.content_type,
        tone=draft.tone,
        topic=draft.topic,
        status=draft.status,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )
