"""Channel binding API route.

Thin router — all orchestration logic lives in :class:`ChannelBindingService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db_session
from app.api.schemas.channel import ChannelBindRequest, ChannelBindResponse
from app.core.config import get_settings
from app.domain.user import User
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.telegram.client import TelegramClient
from app.services.channel_binding import ChannelBindingService

router = APIRouter(
    prefix="/projects/{project_id}/channel",
    tags=["channels"],
)


def _get_channel_binding_service(
    session: AsyncSession = Depends(get_db_session),
) -> ChannelBindingService:
    settings = get_settings()
    bot_token = settings.bot_token.get_secret_value()
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
