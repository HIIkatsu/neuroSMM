"""/start command handler.

Greets the user and presents the main Mini App entry button.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = Router(name="start")

_START_TEXT = (
    "Welcome to NeuroSMM.\n\n"
    "Create and schedule AI-powered social content for your Telegram channels.\n\n"
    "Use the button below to open the app."
)

_START_TEXT_NO_MINIAPP = (
    "Welcome to NeuroSMM.\n\n"
    "The Mini App is not configured yet. Contact your administrator."
)


def build_start_router(settings: Settings | None = None) -> Router:
    """Return the /start router, bound to the provided settings.

    Passing *settings* explicitly keeps the handler testable without
    touching the global config singleton.
    """
    _settings = settings or get_settings()
    _router = Router(name="start")

    @_router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        miniapp_url = _settings.miniapp_url
        if not miniapp_url:
            logger.warning("miniapp_url not configured — /start sent plain text")
            await message.answer(_START_TEXT_NO_MINIAPP)
            return

        await message.answer(
            _START_TEXT,
            reply_markup=main_menu_keyboard(miniapp_url),
        )

    return _router
