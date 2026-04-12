"""/help command handler.

Returns a concise summary of what the bot does and how to use it.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import open_miniapp_keyboard
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_HELP_TEXT = (
    "NeuroSMM — AI content for Telegram channels.\n\n"
    "Commands:\n"
    "/start — show main menu\n"
    "/help  — show this message\n\n"
    "Everything else lives in the Mini App."
)

_HELP_TEXT_NO_MINIAPP = (
    "NeuroSMM — AI content for Telegram channels.\n\n"
    "Commands:\n"
    "/start — show main menu\n"
    "/help  — show this message"
)


def build_help_router(settings: Settings | None = None) -> Router:
    """Return the /help router, bound to the provided settings."""
    _settings = settings or get_settings()
    _router = Router(name="help")

    @_router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        miniapp_url = _settings.miniapp_url
        if not miniapp_url:
            await message.answer(_HELP_TEXT_NO_MINIAPP)
            return

        await message.answer(
            _HELP_TEXT,
            reply_markup=open_miniapp_keyboard(miniapp_url),
        )

    return _router
