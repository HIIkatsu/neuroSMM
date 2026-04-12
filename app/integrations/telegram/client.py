"""Telegram Bot API client for admin verification and publishing.

Isolates all direct Telegram API interaction behind a clean interface.
No aiogram bot objects or Telegram-specific types leak beyond this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


@dataclass(frozen=True)
class ChatAdminInfo:
    """Result of an admin-rights check for a user in a chat.

    Attributes
    ----------
    is_admin : bool
        Whether the user has admin (or creator) rights.
    can_post_messages : bool
        Whether the user can post messages in the channel.
    status : str
        Raw Telegram member status (creator, administrator, member, etc.).
    """

    is_admin: bool
    can_post_messages: bool
    status: str


@dataclass(frozen=True)
class ChatInfo:
    """Basic information about a Telegram chat/channel."""

    chat_id: int
    title: str
    chat_type: str  # "channel", "group", "supergroup", etc.
    username: str | None = None


class TelegramClientError(Exception):
    """Raised when a Telegram API call fails."""


class TelegramClient:
    """Low-level Telegram Bot API client.

    Uses httpx for async HTTP calls.  All Telegram-specific response parsing
    stays inside this class.
    """

    def __init__(self, bot_token: str) -> None:
        if not bot_token:
            raise TelegramClientError("Bot token is required")
        self._base_url = _TELEGRAM_API_BASE.format(token=bot_token)
        self._token = bot_token

    async def get_chat(self, chat_id: str) -> ChatInfo:
        """Fetch basic chat info from Telegram.

        Parameters
        ----------
        chat_id:
            Telegram chat/channel identifier (numeric ID or @username).

        Raises
        ------
        TelegramClientError
            If the API call fails or the chat is not found.
        """
        url = f"{self._base_url}/getChat"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"chat_id": chat_id})
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Telegram getChat failed: %s", exc)
            raise TelegramClientError(f"Telegram API error: {exc}") from exc

        if not data.get("ok"):
            desc = data.get("description", "Unknown error")
            raise TelegramClientError(f"Telegram getChat failed: {desc}")

        result = data["result"]
        return ChatInfo(
            chat_id=result["id"],
            title=result.get("title", ""),
            chat_type=result.get("type", "unknown"),
            username=result.get("username"),
        )

    async def get_chat_member(
        self,
        chat_id: str,
        user_id: int,
    ) -> ChatAdminInfo:
        """Check a user's membership and admin rights in a chat.

        Parameters
        ----------
        chat_id:
            Telegram chat/channel identifier.
        user_id:
            Telegram user ID to check.

        Raises
        ------
        TelegramClientError
            If the API call fails.
        """
        url = f"{self._base_url}/getChatMember"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={"chat_id": chat_id, "user_id": user_id},
                )
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Telegram getChatMember failed: %s", exc)
            raise TelegramClientError(f"Telegram API error: {exc}") from exc

        if not data.get("ok"):
            desc = data.get("description", "Unknown error")
            raise TelegramClientError(f"Telegram getChatMember failed: {desc}")

        result = data["result"]
        status = result.get("status", "")
        is_admin = status in ("creator", "administrator")
        can_post = (
            status == "creator"
            or result.get("can_post_messages", False)
        )

        return ChatAdminInfo(
            is_admin=is_admin,
            can_post_messages=can_post,
            status=status,
        )

    async def send_message(
        self,
        chat_id: str,
        text: str,
    ) -> int:
        """Send a text message to a chat.

        Returns the message_id of the sent message.

        Raises
        ------
        TelegramClientError
            If the API call fails.
        """
        url = f"{self._base_url}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                )
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Telegram sendMessage failed: %s", exc)
            raise TelegramClientError(f"Telegram API error: {exc}") from exc

        if not data.get("ok"):
            desc = data.get("description", "Unknown error")
            raise TelegramClientError(f"Telegram sendMessage failed: {desc}")

        return data["result"]["message_id"]

    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: str | None = None,
    ) -> int:
        """Send a photo (with optional caption) to a chat.

        Returns the message_id of the sent message.

        Raises
        ------
        TelegramClientError
            If the API call fails.
        """
        url = f"{self._base_url}/sendPhoto"
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "photo": photo_url,
        }
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Telegram sendPhoto failed: %s", exc)
            raise TelegramClientError(f"Telegram API error: {exc}") from exc

        if not data.get("ok"):
            desc = data.get("description", "Unknown error")
            raise TelegramClientError(f"Telegram sendPhoto failed: {desc}")

        return data["result"]["message_id"]
