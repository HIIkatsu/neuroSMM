"""Channel binding service.

Orchestrates the flow of binding a Telegram channel to a project:
1. Validate the channel exists via Telegram API
2. Verify the user has admin rights in the channel
3. Persist the channel binding on the project

All Telegram-specific logic is delegated to :class:`TelegramClient`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import AuthorizationError, ExternalServiceError, ValidationError
from app.core.logging import get_logger
from app.domain.project import Project
from app.integrations.db.repositories.project import ProjectRepository
from app.integrations.telegram.client import TelegramClient, TelegramClientError

logger = get_logger(__name__)


@dataclass(frozen=True)
class ChannelBindingResult:
    """Outcome of a channel binding operation.

    Attributes
    ----------
    project : Project
        The project after binding (with platform_channel_id set).
    channel_title : str
        Title of the bound Telegram channel.
    channel_id : str
        Telegram chat ID that was bound.
    """

    project: Project
    channel_title: str
    channel_id: str


class ChannelBindingService:
    """Orchestrates binding a Telegram channel to a user's project."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        telegram_client: TelegramClient,
    ) -> None:
        self._project_repo = project_repo
        self._telegram_client = telegram_client

    async def bind_channel(
        self,
        *,
        project_id: int,
        user_id: int,
        telegram_user_id: int,
        channel_identifier: str,
    ) -> ChannelBindingResult:
        """Bind a Telegram channel to a project.

        Parameters
        ----------
        project_id:
            ID of the project to bind.
        user_id:
            Internal user ID (ownership check).
        telegram_user_id:
            Telegram user ID (admin verification).
        channel_identifier:
            Telegram channel identifier (numeric chat ID or @username).

        Returns
        -------
        ChannelBindingResult
            Contains the updated project and channel info.

        Raises
        ------
        NotFoundError
            If the project does not exist.
        AuthorizationError
            If the user does not own the project or is not an admin in the channel.
        ValidationError
            If the channel identifier is empty or invalid.
        ExternalServiceError
            If Telegram API calls fail.
        """
        if not channel_identifier or not channel_identifier.strip():
            raise ValidationError("Channel identifier must not be empty")

        channel_identifier = channel_identifier.strip()

        # 1. Verify project ownership
        project = await self._project_repo.get_by_id(project_id)
        if project.owner_id != user_id:
            raise AuthorizationError("You do not have access to this project")

        # 2. Verify the channel exists
        try:
            chat_info = await self._telegram_client.get_chat(channel_identifier)
        except TelegramClientError as exc:
            raise ExternalServiceError(
                f"Could not verify channel: {exc}"
            ) from exc

        # 3. Verify admin rights
        try:
            admin_info = await self._telegram_client.get_chat_member(
                chat_id=channel_identifier,
                user_id=telegram_user_id,
            )
        except TelegramClientError as exc:
            raise ExternalServiceError(
                f"Could not verify admin rights: {exc}"
            ) from exc

        if not admin_info.is_admin:
            raise AuthorizationError(
                "You must be an admin of the target channel to bind it"
            )

        if not admin_info.can_post_messages:
            raise AuthorizationError(
                "You do not have permission to post messages in the target channel"
            )

        # 4. Persist the binding
        # Use the numeric chat_id from Telegram (authoritative)
        bound_channel_id = str(chat_info.chat_id)
        updated_project = project.link_channel(bound_channel_id)
        saved_project = await self._project_repo.update(updated_project)

        logger.info(
            "Bound channel %s (%s) to project %d",
            chat_info.title,
            bound_channel_id,
            project_id,
        )

        return ChannelBindingResult(
            project=saved_project,
            channel_title=chat_info.title,
            channel_id=bound_channel_id,
        )
