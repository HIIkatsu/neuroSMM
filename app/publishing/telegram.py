"""Real Telegram publisher implementation.

Implements the :class:`Publisher` protocol using :class:`TelegramClient`
to send posts to Telegram channels.  Telegram-specific objects do not
leak beyond this module — only :class:`PublishPayload` and
:class:`PublishResult` cross the boundary.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.integrations.telegram.client import TelegramClient, TelegramClientError
from app.publishing.provider import PublishPayload, PublishResult

logger = get_logger(__name__)


class TelegramPublisher:
    """Publisher that sends content to a Telegram channel.

    Satisfies the :class:`Publisher` protocol.

    Parameters
    ----------
    client:
        An initialised :class:`TelegramClient` instance.
    """

    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    async def publish(self, payload: PublishPayload) -> PublishResult:
        """Publish content to the specified Telegram channel.

        Supports:
        - text-only publish (sendMessage)
        - text + image publish (sendPhoto with caption)

        Returns a :class:`PublishResult` with the Telegram message_id on
        success, or an error message on failure.
        """
        if not payload.channel_id:
            return PublishResult(
                success=False,
                error_message="No target channel configured for this project",
            )

        try:
            if payload.image_url:
                # Text + image → sendPhoto with caption
                message_id = await self._client.send_photo(
                    chat_id=payload.channel_id,
                    photo_url=payload.image_url,
                    caption=payload.text or None,
                )
            else:
                # Text-only → sendMessage
                if not payload.text:
                    return PublishResult(
                        success=False,
                        error_message="Nothing to publish: no text and no image",
                    )
                message_id = await self._client.send_message(
                    chat_id=payload.channel_id,
                    text=payload.text,
                )

            logger.info(
                "Published to Telegram channel %s, message_id=%d",
                payload.channel_id,
                message_id,
            )
            return PublishResult(
                success=True,
                platform_post_id=str(message_id),
            )

        except TelegramClientError as exc:
            logger.error(
                "Telegram publish failed for channel %s: %s",
                payload.channel_id,
                exc,
            )
            return PublishResult(
                success=False,
                error_message=str(exc),
            )
