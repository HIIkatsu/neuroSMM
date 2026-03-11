from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Config:
    bot_token: str
    tz: str
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_model: str
    admin_ids: set[int]


def _parse_admin_ids(s: str) -> set[int]:
    out: set[int] = set()
    for part in (s or "").replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            pass
    return out


def load_config() -> Config:
    bot_token = (os.getenv("BOT_TOKEN") or "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is missing in .env")

    # поддерживаем оба варианта
    tz = (os.getenv("BOT_TZ") or os.getenv("TZ") or "Europe/Moscow").strip()

    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    # (на всякий) если где-то использовалась другая переменная
    if not key:
        key = (os.getenv("OPENAI_API_KEY") or "").strip()

    base_url = (os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1").strip()
    model = (os.getenv("OPENROUTER_MODEL") or "gpt-4o-mini").strip()

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

    return Config(
        bot_token=bot_token,
        tz=tz,
        openrouter_api_key=key,
        openrouter_base_url=base_url,
        openrouter_model=model,
        admin_ids=admin_ids,
    )