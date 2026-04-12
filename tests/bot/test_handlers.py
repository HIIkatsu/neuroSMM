"""Unit tests for /start and /help handler routing.

We test the handler functions in isolation by:
1. Calling build_start_router / build_help_router with test Settings
2. Creating a mock Message and calling the inner handler directly
3. Asserting on the reply content and keyboards

This approach avoids standing up a real bot or a full aiogram event loop.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.help import build_help_router
from app.bot.handlers.start import build_start_router
from app.core.config import Settings


def _make_message() -> AsyncMock:
    """Return a minimal mock Message with an async answer() method."""
    message = AsyncMock()
    message.answer = AsyncMock()
    return message


def _get_handler(router: Any) -> Any:
    """Extract the single registered message handler callable from a Router."""
    # aiogram 3.x stores observers under router.message
    handlers = router.message.handlers
    assert len(handlers) == 1, f"Expected 1 handler, got {len(handlers)}"
    return handlers[0].callback


class TestStartHandler:
    async def test_start_replies_with_text(self, settings_with_miniapp: Settings) -> None:
        router = build_start_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        message.answer.assert_called_once()

    async def test_start_includes_keyboard_when_miniapp_configured(
        self, settings_with_miniapp: Settings
    ) -> None:
        router = build_start_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        _, kwargs = message.answer.call_args
        keyboard = kwargs.get("reply_markup")
        assert keyboard is not None, "Expected reply_markup with Mini App keyboard"

    async def test_start_keyboard_contains_miniapp_url(
        self, settings_with_miniapp: Settings
    ) -> None:
        router = build_start_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        _, kwargs = message.answer.call_args
        keyboard = kwargs["reply_markup"]
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        urls = [b.web_app.url for b in all_buttons if b.web_app]
        assert any(settings_with_miniapp.miniapp_url in url for url in urls)

    async def test_start_no_keyboard_when_miniapp_not_configured(
        self, settings_no_miniapp: Settings
    ) -> None:
        router = build_start_router(settings_no_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        message.answer.assert_called_once()
        _, kwargs = message.answer.call_args
        assert kwargs.get("reply_markup") is None

    async def test_start_text_mentions_welcome(self, settings_with_miniapp: Settings) -> None:
        router = build_start_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        args, _ = message.answer.call_args
        text: str = args[0]
        assert "Welcome" in text or "welcome" in text.lower()


class TestHelpHandler:
    async def test_help_replies_with_text(self, settings_with_miniapp: Settings) -> None:
        router = build_help_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        message.answer.assert_called_once()

    async def test_help_includes_keyboard_when_miniapp_configured(
        self, settings_with_miniapp: Settings
    ) -> None:
        router = build_help_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        _, kwargs = message.answer.call_args
        keyboard = kwargs.get("reply_markup")
        assert keyboard is not None

    async def test_help_keyboard_has_miniapp_url(self, settings_with_miniapp: Settings) -> None:
        router = build_help_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        _, kwargs = message.answer.call_args
        keyboard = kwargs["reply_markup"]
        all_buttons = [btn for row in keyboard.inline_keyboard for btn in row]
        urls = [b.web_app.url for b in all_buttons if b.web_app]
        assert any(settings_with_miniapp.miniapp_url in url for url in urls)

    async def test_help_no_keyboard_when_miniapp_not_configured(
        self, settings_no_miniapp: Settings
    ) -> None:
        router = build_help_router(settings_no_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        _, kwargs = message.answer.call_args
        assert kwargs.get("reply_markup") is None

    async def test_help_text_lists_commands(self, settings_with_miniapp: Settings) -> None:
        router = build_help_router(settings_with_miniapp)
        handler = _get_handler(router)
        message = _make_message()
        await handler(message)
        args, _ = message.answer.call_args
        text: str = args[0]
        assert "/start" in text
        assert "/help" in text
