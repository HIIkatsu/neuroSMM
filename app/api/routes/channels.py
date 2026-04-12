"""Channel binding API route.

Thin router — all orchestration logic lives in :class:`ChannelBindingService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.channel import ChannelBindRequest, ChannelBindResponse, ChannelStatusResponse
from app.core.config import get_settings
from app.domain.user import User
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.telegram.client import TelegramClient
from app.services.channel_binding import ChannelBindingService
from app.services.project import ProjectService

router = APIRouter(
    prefix="/projects/{project_id}/channel",
    tags=["channels"],
)


def _get_channel_binding_service(
    session: AsyncSession = Depends(get_db_session),
) -> ChannelBindingService:
    settings = get_settings()
    bot_token = settings.bot_token.get_secret_value()
    if not bot_token:
        from app.core.exceptions import ConfigurationError

        raise ConfigurationError("Telegram bot token is not configured for channel binding")
    telegram_client = TelegramClient(bot_token)
    return ChannelBindingService(
        project_repo=ProjectRepository(session),
        telegram_client=telegram_client,
    )


@router.post(
    "/bind",
    response_model=ChannelBindResponse,
    summary="Bind a Telegram channel to a project",
)
async def bind_channel(
    project_id: int,
    body: ChannelBindRequest,
    user: User = Depends(get_current_user),
    service: ChannelBindingService = Depends(_get_channel_binding_service),
) -> ChannelBindResponse:
    """Bind a Telegram channel to a project.

    Verifies that the channel exists and the user has admin rights
    before persisting the binding.
    """
    assert user.id is not None
    result = await service.bind_channel(
        project_id=project_id,
        user_id=user.id,
        telegram_user_id=user.telegram_id,
        channel_identifier=body.channel_identifier,
    )
    return ChannelBindResponse(
        project_id=result.project.id,  # type: ignore[arg-type]
        channel_id=result.channel_id,
        channel_title=result.channel_title,
    )


def _get_project_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProjectService:
    return ProjectService(ProjectRepository(session))


@router.get(
    "/status",
    response_model=ChannelStatusResponse,
    summary="Get channel binding status for a project",
)
async def channel_status(
    project_id: int,
    user: User = Depends(get_current_user),
    service: ProjectService = Depends(_get_project_service),
) -> ChannelStatusResponse:
    """Return whether a project has a bound channel and its identifier.

    This is a lightweight read-only check that the Mini App uses to show
    channel binding status in the project detail view.
    """
    assert user.id is not None
    project = await service.get_project(project_id=project_id, user_id=user.id)
    is_bound = project.platform_channel_id is not None
    return ChannelStatusResponse(
        project_id=project.id,  # type: ignore[arg-type]
        is_bound=is_bound,
        channel_id=project.platform_channel_id,
    )
