"""
Telegram bot application factory for NeuroSMM V2.

Creates and configures an aiogram :class:`Bot` and :class:`Dispatcher`.
Actual handlers/routers will be registered in PR 09.

Usage::

    import asyncio
    from app.bot.app import create_bot, create_dispatcher

    bot = create_bot()
    dp  = create_dispatcher()
    asyncio.run(dp.start_polling(bot))
"""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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


def create_dispatcher() -> Dispatcher:
    """Return a configured :class:`Dispatcher`.

    Handlers / routers will be attached in later PRs (PR 09).
    """
    dp = Dispatcher()
    logger.info("Dispatcher created (no routers attached yet)")
    return dp
