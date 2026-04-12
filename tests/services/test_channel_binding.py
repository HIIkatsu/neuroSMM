"""Tests for the ChannelBindingService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, ExternalServiceError, ValidationError
from app.domain.project import Project
from app.integrations.telegram.client import ChatAdminInfo, ChatInfo, TelegramClientError
from app.services.channel_binding import ChannelBindingResult, ChannelBindingService


def _make_project(
    *,
    project_id: int = 1,
    owner_id: int = 1,
    channel_id: str | None = None,
) -> Project:
    return Project(
        id=project_id,
        owner_id=owner_id,
        title="Test Project",
        platform_channel_id=channel_id,
    )


def _make_chat_info(
    *,
    chat_id: int = -1001234567890,
    title: str = "My Channel",
    chat_type: str = "channel",
    username: str | None = "mychannel",
) -> ChatInfo:
    return ChatInfo(
        chat_id=chat_id,
        title=title,
        chat_type=chat_type,
        username=username,
    )


def _make_admin_info(
    *,
    is_admin: bool = True,
    can_post_messages: bool = True,
    status: str = "administrator",
) -> ChatAdminInfo:
    return ChatAdminInfo(
        is_admin=is_admin,
        can_post_messages=can_post_messages,
        status=status,
    )


def _build_service(
    *,
    project: Project | None = None,
    chat_info: ChatInfo | None = None,
    admin_info: ChatAdminInfo | None = None,
    get_chat_error: Exception | None = None,
    get_member_error: Exception | None = None,
) -> ChannelBindingService:
    """Build a ChannelBindingService with mocked dependencies."""
    project_repo = AsyncMock()
    telegram_client = AsyncMock()

    if project is not None:
        project_repo.get_by_id.return_value = project
        project_repo.update.side_effect = lambda p: p

    if chat_info is not None:
        telegram_client.get_chat.return_value = chat_info
    elif get_chat_error is not None:
        telegram_client.get_chat.side_effect = get_chat_error

    if admin_info is not None:
        telegram_client.get_chat_member.return_value = admin_info
    elif get_member_error is not None:
        telegram_client.get_chat_member.side_effect = get_member_error

    return ChannelBindingService(project_repo, telegram_client)


class TestBindChannel:
    """Tests for ChannelBindingService.bind_channel."""

    async def test_successful_binding(self) -> None:
        """Channel binding succeeds with valid admin rights."""
        project = _make_project()
        chat_info = _make_chat_info()
        admin_info = _make_admin_info()
        service = _build_service(
            project=project, chat_info=chat_info, admin_info=admin_info
        )

        result = await service.bind_channel(
            project_id=1,
            user_id=1,
            telegram_user_id=12345,
            channel_identifier="@mychannel",
        )

        assert isinstance(result, ChannelBindingResult)
        assert result.channel_title == "My Channel"
        assert result.channel_id == str(chat_info.chat_id)
        assert result.project.platform_channel_id == str(chat_info.chat_id)

    async def test_ownership_enforced(self) -> None:
        """Binding fails if user does not own the project."""
        project = _make_project(owner_id=99)
        service = _build_service(project=project)

        with pytest.raises(AuthorizationError, match="access"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="@mychannel",
            )

    async def test_empty_channel_identifier_rejected(self) -> None:
        """Empty channel identifier raises ValidationError."""
        project = _make_project()
        service = _build_service(project=project)

        with pytest.raises(ValidationError, match="empty"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="",
            )

    async def test_whitespace_channel_identifier_rejected(self) -> None:
        """Whitespace-only channel identifier raises ValidationError."""
        project = _make_project()
        service = _build_service(project=project)

        with pytest.raises(ValidationError, match="empty"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="   ",
            )

    async def test_channel_not_found_raises_external_error(self) -> None:
        """Telegram API failure for get_chat raises ExternalServiceError."""
        project = _make_project()
        service = _build_service(
            project=project,
            get_chat_error=TelegramClientError("Chat not found"),
        )

        with pytest.raises(ExternalServiceError, match="verify channel"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="@nonexistent",
            )

    async def test_admin_check_failure_raises_external_error(self) -> None:
        """Telegram API failure for getChatMember raises ExternalServiceError."""
        project = _make_project()
        chat_info = _make_chat_info()
        service = _build_service(
            project=project,
            chat_info=chat_info,
            get_member_error=TelegramClientError("User not found"),
        )

        with pytest.raises(ExternalServiceError, match="admin rights"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="@mychannel",
            )

    async def test_not_admin_raises_authorization_error(self) -> None:
        """Non-admin user cannot bind a channel."""
        project = _make_project()
        chat_info = _make_chat_info()
        admin_info = _make_admin_info(is_admin=False, status="member")
        service = _build_service(
            project=project, chat_info=chat_info, admin_info=admin_info
        )

        with pytest.raises(AuthorizationError, match="admin"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="@mychannel",
            )

    async def test_no_post_permission_raises_authorization_error(self) -> None:
        """Admin without post permission cannot bind a channel."""
        project = _make_project()
        chat_info = _make_chat_info()
        admin_info = _make_admin_info(
            is_admin=True, can_post_messages=False, status="administrator"
        )
        service = _build_service(
            project=project, chat_info=chat_info, admin_info=admin_info
        )

        with pytest.raises(AuthorizationError, match="post messages"):
            await service.bind_channel(
                project_id=1,
                user_id=1,
                telegram_user_id=12345,
                channel_identifier="@mychannel",
            )

    async def test_creator_status_always_succeeds(self) -> None:
        """Channel creator should always pass admin and post checks."""
        project = _make_project()
        chat_info = _make_chat_info()
        admin_info = _make_admin_info(
            is_admin=True, can_post_messages=True, status="creator"
        )
        service = _build_service(
            project=project, chat_info=chat_info, admin_info=admin_info
        )

        result = await service.bind_channel(
            project_id=1,
            user_id=1,
            telegram_user_id=12345,
            channel_identifier="@mychannel",
        )

        assert result.channel_title == "My Channel"

    async def test_numeric_chat_id_used_for_binding(self) -> None:
        """The numeric chat_id from Telegram is used, not the input identifier."""
        project = _make_project()
        chat_info = _make_chat_info(chat_id=-1009999999999)
        admin_info = _make_admin_info()
        service = _build_service(
            project=project, chat_info=chat_info, admin_info=admin_info
        )

        result = await service.bind_channel(
            project_id=1,
            user_id=1,
            telegram_user_id=12345,
            channel_identifier="@mychannel",
        )

        assert result.channel_id == "-1009999999999"
        assert result.project.platform_channel_id == "-1009999999999"

    async def test_project_repo_update_called(self) -> None:
        """The project repository update method should be called."""
        project = _make_project()
        chat_info = _make_chat_info()
        admin_info = _make_admin_info()
        service = _build_service(
            project=project, chat_info=chat_info, admin_info=admin_info
        )

        await service.bind_channel(
            project_id=1,
            user_id=1,
            telegram_user_id=12345,
            channel_identifier="@mychannel",
        )

        service._project_repo.update.assert_called_once()
