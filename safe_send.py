
from aiogram.exceptions import TelegramBadRequest


async def safe_send(bot, chat_id: int | str, text: str, reply_markup=None):
    try:
        return await bot.send_message(chat_id, text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        print("Telegram error:", e)
        return False
    except Exception as e:
        print("Send error:", e)
        return False


async def safe_send_photo(bot, chat_id: int | str, photo: str, caption: str, reply_markup=None):
    try:
        return await bot.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        print("Telegram error:", e)
        return False
    except Exception as e:
        print("Send photo error:", e)
        return False


async def answer_plain(message, text: str, reply_markup=None):
    try:
        await message.answer(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        print("Telegram error:", e)
    except Exception as e:
        print("Answer error:", e)
