"""
Telegram bot application factory for NeuroSMM V2.

Creates and configures an aiogram :class:`Bot` and :class:`Dispatcher`
with all command routers wired in.

Usage::

    import asyncio
    from app.bot.app import create_bot, create_dispatcher

    settings = get_settings()
    bot = create_bot(settings)
    dp  = create_dispatcher(settings)
    asyncio.run(dp.start_polling(bot))
"""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.help import build_help_router
from app.bot.handlers.start import build_start_router
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_bot(settings: Settings | None = None) -> Bot:
    """Return a configured :class:`Bot` instance."""
    settings = settings or get_settings()
    token = settings.bot_token.get_secret_value()
    if not token:
        raise RuntimeError("BOT_TOKEN is not configured — cannot create bot instance")

    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(settings: Settings | None = None) -> Dispatcher:
    """Return a configured :class:`Dispatcher` with all handlers wired.

    Parameters
    ----------
    settings:
        Optional settings override.  Passed through to each router builder
        so that Mini App URL and other config stay testable.
    """
    _settings = settings or get_settings()
    dp = Dispatcher()

    dp.include_router(build_start_router(_settings))
    dp.include_router(build_help_router(_settings))

    logger.info("Dispatcher created with start/help routers")
    return dp
