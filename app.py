
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import load_config
from db import init_db
from scheduler_service import SchedulerService

from handlers_private import router as private_router
from handlers_admin import router as admin_router
from handlers_chat import router as chat_router

logging.basicConfig(level=logging.INFO)

async def main():
    config = load_config()
    await init_db()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=None))
    bot._config = config

    dp = Dispatcher()
    bot._dp = dp  # for admin helper

    scheduler = SchedulerService(bot=bot, tz=config.tz)
    scheduler.start()
    await scheduler.rebuild_jobs()

    dp["config"] = config
    dp["scheduler"] = scheduler

    dp.include_router(private_router)
    dp.include_router(admin_router)
    dp.include_router(chat_router)

    logging.info("BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
