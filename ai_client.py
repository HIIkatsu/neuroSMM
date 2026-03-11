from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx
from openai import OpenAI
from openai import APITimeoutError, APIConnectionError, RateLimitError, APIError

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def make_client(api_key: str, base_url: Optional[str] = None) -> OpenAI:
    """
    Важно:
    - trust_env=False => игнорируем HTTP(S)_PROXY из окружения (они часто ломают TLS handshake).
    - увеличенные таймауты.
    """
    base_url = (base_url or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL).strip()

    timeout = httpx.Timeout(
        connect=15.0,   # TLS handshake
        read=60.0,      # ожидание ответа модели
        write=30.0,
        pool=60.0,
    )

    http_client = httpx.Client(timeout=timeout, trust_env=False)

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=http_client,
    )


async def ai_chat(
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.6,
    base_url: Optional[str] = None,
) -> str:
    """
    openai-python 1.x синхронный клиент -> запускаем в отдельном треде.
    Возвращаем текст, а ошибки превращаем в человекопонятный ответ (чтобы бот не падал).
    """
    client = make_client(api_key, base_url=base_url)

    def _call() -> str:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return (r.choices[0].message.content or "").strip()

    try:
        return await asyncio.to_thread(_call)

    except APITimeoutError:
        return "⏳ Я немного завис на запросе к нейросети (таймаут). Попробуй ещё раз через 5–10 секунд."

    except RateLimitError:
        return "⚠️ Сейчас лимит запросов к нейросети. Попробуй позже."

    except APIConnectionError:
        return "🌐 Не могу подключиться к нейросети (проблема соединения). Проверь интернет/прокси/VPN."

    except APIError as e:
        return f"⚠️ Ошибка нейросети: {type(e).__name__}. Попробуй ещё раз."

    except Exception as e:
        return f"⚠️ Неожиданная ошибка: {type(e).__name__}. Попробуй ещё раз."