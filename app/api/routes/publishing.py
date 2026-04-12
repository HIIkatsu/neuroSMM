"""Preview and publish API routes.

Thin router — all orchestration logic lives in :class:`PreviewService`
and :class:`PublishService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.publishing import PreviewResponse, PublishResponse
from app.core.config import get_settings
from app.domain.user import User
from app.integrations.db.repositories.draft import DraftRepository
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.telegram.client import TelegramClient
from app.publishing.provider import Publisher, StubPublisher
from app.publishing.telegram import TelegramPublisher
from app.services.preview import PreviewService
from app.services.publish import PublishService

router = APIRouter(
    prefix="/projects/{project_id}/drafts/{draft_id}",
    tags=["publishing"],
)


def _get_preview_service(
    session: AsyncSession = Depends(get_db_session),
) -> PreviewService:
    return PreviewService(DraftRepository(session), ProjectRepository(session))


def _get_publisher() -> Publisher:
    """Create the appropriate publisher based on configuration.

    Uses :class:`TelegramPublisher` when a bot token is configured,
    otherwise falls back to :class:`StubPublisher` (dev/test only).
    """
    settings = get_settings()
    bot_token = settings.bot_token.get_secret_value()
    if bot_token:
        client = TelegramClient(bot_token)
        return TelegramPublisher(client)
    return StubPublisher()


def _get_publish_service(
    session: AsyncSession = Depends(get_db_session),
) -> PublishService:
    return PublishService(
        DraftRepository(session),
        ProjectRepository(session),
        _get_publisher(),
    )


@router.get(
    "/preview",
    response_model=PreviewResponse,
    summary="Preview a draft",
)
async def preview_draft(
    project_id: int,
    draft_id: int,
    user: User = Depends(get_current_user),
    service: PreviewService = Depends(_get_preview_service),
) -> PreviewResponse:
    """Return a preview-ready representation of the draft.

    Validates ownership and draft state before building the preview.
    """
    assert user.id is not None
    payload = await service.get_preview(draft_id=draft_id, user_id=user.id)
    return PreviewResponse(
        draft_id=payload.draft_id,
        project_id=payload.project_id,
        title=payload.title,
        text_content=payload.text_content,
        image_url=payload.image_url,
        content_type=payload.content_type,
        tone=payload.tone,
        status=payload.status,
        created_at=payload.created_at,
        updated_at=payload.updated_at,
    )


@router.post(
    "/publish",
    response_model=PublishResponse,
    summary="Publish a draft",
)
async def publish_draft(
    project_id: int,
    draft_id: int,
    user: User = Depends(get_current_user),
    service: PublishService = Depends(_get_publish_service),
) -> PublishResponse:
    """Publish a READY draft through the publisher abstraction.

    Enforces ownership and READY state. Transitions draft to PUBLISHED
    on success.
    """
    assert user.id is not None
    outcome = await service.publish_draft(draft_id=draft_id, user_id=user.id)
    return PublishResponse(
        draft_id=outcome.draft.id,  # type: ignore[arg-type]
        status=outcome.draft.status,
        platform_post_id=outcome.platform_post_id,
        published=outcome.success,
    )
