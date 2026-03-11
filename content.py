from __future__ import annotations

from db import get_setting
from ai_client import ai_chat


_ERROR_PREFIXES = ("⚠️", "⏳", "🌐")


def _looks_like_ai_error(text: str) -> bool:
    t = (text or "").strip()
    return (not t) or t.startswith(_ERROR_PREFIXES)


def _local_fallback_post(topic: str, prompt: str) -> str:
    subject = (prompt or topic or "теме канала").strip()
    headline = subject[:1].upper() + subject[1:] if subject else "Новая публикация"
    return (
        f"{headline}\n\n"
        f"Сегодня разберём тему: {subject}.\n"
        f"— что в ней действительно важно прямо сейчас;\n"
        f"— на что люди чаще всего не обращают внимания;\n"
        f"— с какого простого шага лучше начать;\n"
        f"— каких ошибок стоит избегать;\n"
        f"— как применить это на практике уже сегодня.\n\n"
        f"Если хочешь, могу дальше сделать по этой теме серию более узких и полезных постов."
    ).strip()


async def generate_post_text(api_key: str, model: str, *, topic: str, prompt: str = "", base_url: str | None = None) -> str:
    no_disclaimer = (await get_setting("no_disclaimer") or "1") == "1"

    user_prompt = (
        "Ты пишешь пост для Telegram-канала. "
        "Пиши по-русски, живо, понятно и по делу. "
        "Без Markdown, без HTML, без фраз про ИИ. "
        "Сделай короткий заголовок и затем 5-10 строк полезного текста.\n"
    )
    if no_disclaimer:
        user_prompt += "Не добавляй дисклеймеры и формальные оговорки.\n"
    user_prompt += f"Тема канала: {(topic or '').strip() or 'без общей темы'}\n"
    if prompt.strip():
        user_prompt += f"Точная тема поста: {prompt.strip()}\n"
    else:
        user_prompt += "Сделай один качественный пост для этого канала.\n"

    txt = await ai_chat(
        api_key=api_key,
        model=model,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.7,
        base_url=base_url,
    )

    if _looks_like_ai_error(txt):
        retry_prompt = (
            f"Напиши Telegram-пост на русском по теме '{(prompt or topic or 'канал').strip()}'. "
            "Без Markdown и без упоминания ИИ. "
            "Сначала короткий заголовок, потом 5-8 строк текста."
        )
        txt = await ai_chat(
            api_key=api_key,
            model=model,
            messages=[{"role": "user", "content": retry_prompt}],
            temperature=0.5,
            base_url=base_url,
        )

    if _looks_like_ai_error(txt):
        txt = _local_fallback_post(topic, prompt)

    txt = txt.replace("**", "").replace("__", "")
    return txt.strip()
