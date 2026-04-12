"""Tests for the TelegramPublisher."""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.integrations.telegram.client import TelegramClient, TelegramClientError
from app.publishing.provider import PublishPayload, PublishResult
from app.publishing.telegram import TelegramPublisher


def _make_publisher(client: AsyncMock | None = None) -> tuple[TelegramPublisher, AsyncMock]:
    """Build a TelegramPublisher with a mocked TelegramClient."""
    if client is None:
        client = AsyncMock(spec=TelegramClient)
    publisher = TelegramPublisher(client)
    return publisher, client


class TestTelegramPublisher:
    """Tests for TelegramPublisher.publish."""

    async def test_text_only_publish_success(self) -> None:
        """Text-only publish calls sendMessage and returns success."""
        publisher, client = _make_publisher()
        client.send_message.return_value = 42

        payload = PublishPayload(text="Hello world", channel_id="@mychannel")
        result = await publisher.publish(payload)

        assert result.success is True
        assert result.platform_post_id == "42"
        assert result.error_message is None
        client.send_message.assert_called_once_with(
            chat_id="@mychannel",
            text="Hello world",
        )

    async def test_text_and_image_publish_success(self) -> None:
        """Text + image publish calls sendPhoto and returns success."""
        publisher, client = _make_publisher()
        client.send_photo.return_value = 99

        payload = PublishPayload(
            text="Caption text",
            image_url="https://img.test/photo.jpg",
            channel_id="@mychannel",
        )
        result = await publisher.publish(payload)

        assert result.success is True
        assert result.platform_post_id == "99"
        client.send_photo.assert_called_once_with(
            chat_id="@mychannel",
            photo_url="https://img.test/photo.jpg",
            caption="Caption text",
        )

    async def test_image_only_publish_success(self) -> None:
        """Image-only publish (no text) calls sendPhoto without caption."""
        publisher, client = _make_publisher()
        client.send_photo.return_value = 77

        payload = PublishPayload(
            text="",
            image_url="https://img.test/photo.jpg",
            channel_id="@mychannel",
        )
        result = await publisher.publish(payload)

        assert result.success is True
        assert result.platform_post_id == "77"
        client.send_photo.assert_called_once_with(
            chat_id="@mychannel",
            photo_url="https://img.test/photo.jpg",
            caption=None,
        )

    async def test_missing_channel_returns_failure(self) -> None:
        """Publish without channel_id returns a failure result."""
        publisher, client = _make_publisher()

        payload = PublishPayload(text="Hello", channel_id=None)
        result = await publisher.publish(payload)

        assert result.success is False
        assert "No target channel" in (result.error_message or "")
        client.send_message.assert_not_called()

    async def test_empty_text_and_no_image_returns_failure(self) -> None:
        """Nothing to publish returns a failure result."""
        publisher, client = _make_publisher()

        payload = PublishPayload(text="", image_url=None, channel_id="@ch")
        result = await publisher.publish(payload)

        assert result.success is False
        assert "Nothing to publish" in (result.error_message or "")

    async def test_telegram_api_failure_returns_error_result(self) -> None:
        """Telegram API failure is caught and returned as a failure result."""
        publisher, client = _make_publisher()
        client.send_message.side_effect = TelegramClientError("Bot was blocked")

        payload = PublishPayload(text="Hello", channel_id="@ch")
        result = await publisher.publish(payload)

        assert result.success is False
        assert "Bot was blocked" in (result.error_message or "")

    async def test_telegram_photo_api_failure_returns_error_result(self) -> None:
        """Photo API failure is caught and returned as a failure result."""
        publisher, client = _make_publisher()
        client.send_photo.side_effect = TelegramClientError("Photo too large")

        payload = PublishPayload(
            text="Caption",
            image_url="https://img.test/big.jpg",
            channel_id="@ch",
        )
        result = await publisher.publish(payload)

        assert result.success is False
        assert "Photo too large" in (result.error_message or "")

    async def test_publish_result_type(self) -> None:
        """Publish always returns a PublishResult."""
        publisher, client = _make_publisher()
        client.send_message.return_value = 1

        payload = PublishPayload(text="Test", channel_id="@ch")
        result = await publisher.publish(payload)

        assert isinstance(result, PublishResult)

    async def test_message_id_is_string(self) -> None:
        """Platform post ID is always a string representation of message_id."""
        publisher, client = _make_publisher()
        client.send_message.return_value = 12345

        payload = PublishPayload(text="Test", channel_id="@ch")
        result = await publisher.publish(payload)

        assert result.platform_post_id == "12345"
        assert isinstance(result.platform_post_id, str)
