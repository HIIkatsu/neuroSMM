from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import re

import db
from content import generate_post_text
from image_search import find_image
from safe_send import safe_send, safe_send_photo


@dataclass
class ActionResult:
    ok: bool
    error: str | None = None


# ---------- ХЕШТЕГИ ----------

def generate_hashtags(topic: str, text: str) -> str:
    words = []

    for w in re.findall(r"[a-zA-Zа-яА-Я0-9]+", topic + " " + text):
        w = w.lower()
        if len(w) < 4:
            continue
        words.append(w)

    uniq = []
    for w in words:
        if w not in uniq:
            uniq.append(w)

    tags = uniq[:5]

    if not tags:
        return ""

    return " ".join("#" + t for t in tags)


# ---------- PAYLOAD ----------

async def generate_post_payload(
    config: Any,
    prompt: str = "",
    *,
    owner_id: int | None = 0,
    force_image: bool = True
) -> dict:

    topic = await db.get_setting("topic", owner_id=owner_id) or ""

    text = await generate_post_text(
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
        topic=topic,
        prompt=prompt,
        base_url=getattr(config, "openrouter_base_url", None),
    )

    
    image_ref = ""
    if force_image:
        image_ref = await find_image((prompt or topic).strip() or topic) or ""

    return {
        "text": text,
        "prompt": prompt,
        "topic": topic,
        "media_type": "photo" if image_ref else "none",
        "media_ref": image_ref,
        "buttons_json": "[]",
        "pin_post": 0,
        "comments_enabled": 1,
        "ad_mark": 0,
        "first_reaction": "",
        "reply_to_message_id": 0,
    }


# ---------- СОЗДАНИЕ ЧЕРНОВИКА ----------

async def create_generated_draft(
    config: Any,
    prompt: str,
    *,
    owner_id: int | None = 0,
    force_image: bool = True
) -> int:

    channel = await db.get_setting("channel_target", owner_id=owner_id) or ""

    payload = await generate_post_payload(
        config,
        prompt,
        owner_id=owner_id,
        force_image=force_image
    )

    draft_id = await db.create_draft(
        owner_id=owner_id,
        channel_target=channel,
        text=payload["text"],
        prompt=payload["prompt"],
        topic=payload["topic"],
        media_type=payload["media_type"],
        media_ref=payload["media_ref"],
        buttons_json=payload["buttons_json"],
        pin_post=payload["pin_post"],
        comments_enabled=payload["comments_enabled"],
        ad_mark=payload["ad_mark"],
        first_reaction=payload["first_reaction"],
        reply_to_message_id=payload["reply_to_message_id"],
        status="draft",
    )

    return draft_id


# ---------- INLINE КНОПКИ ----------

def _build_reply_markup_from_buttons(buttons_json: str):
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        data = json.loads(buttons_json or "[]")

        if not data:
            return None

        rows = []

        for item in data:
            txt = (item.get("text") or "").strip()
            url = (item.get("url") or "").strip()

            if txt and url:
                rows.append([InlineKeyboardButton(text=txt, url=url)])

        if not rows:
            return None

        return InlineKeyboardMarkup(inline_keyboard=rows)

    except Exception:
        return None


# ---------- ПРЕДПРОСМОТР ----------

async def send_draft_preview(target, bot, draft: dict, *, owner_id: int | None = 0):

    reply_markup = _build_reply_markup_from_buttons(draft.get("buttons_json", "[]"))

    text = draft.get("text", "")
    media_type = (draft.get("media_type") or "none").strip()
    media_ref = (draft.get("media_ref") or "").strip()

    if media_type == "photo" and media_ref:
        return await target.answer_photo(
            photo=media_ref,
            caption=text,
            reply_markup=reply_markup,
        )

    return await target.answer(
        text,
        reply_markup=reply_markup,
    )


# ---------- ПУБЛИКАЦИЯ ----------

async def publish_draft(bot, draft: dict, *, owner_id: int | None = 0) -> ActionResult:

    channel = draft.get("channel_target") or await db.get_setting(
        "channel_target",
        owner_id=owner_id,
    )

    if not channel:
        return ActionResult(False, "Канал не привязан")

    text = draft.get("text", "")

    media_type = (draft.get("media_type") or "none").strip()
    media_ref = (draft.get("media_ref") or "").strip()

    reply_markup = _build_reply_markup_from_buttons(
        draft.get("buttons_json", "[]")
    )

    try:

        if media_type == "photo" and media_ref:

            msg = await safe_send_photo(
                bot,
                channel,
                photo=media_ref,
                caption=text,
                reply_markup=reply_markup,
            )

            content_type = "photo"

        else:

            msg = await safe_send(
                bot,
                channel,
                text,
                reply_markup=reply_markup,
            )

            content_type = "text"

        if not msg:
            return ActionResult(False, "Ошибка отправки в Telegram")

        if int(draft.get("pin_post", 0)):

            try:
                await bot.pin_chat_message(
                    channel,
                    getattr(msg, "message_id", 0),
                    disable_notification=True,
                )
            except Exception:
                pass

        await db.log_post(
            owner_id=owner_id,
            channel_target=channel,
            content_type=content_type,
            text=text,
            prompt=draft.get("prompt", ""),
            topic=draft.get("topic", ""),
            file_id=media_ref or "",
            telegram_message_id=getattr(msg, "message_id", 0),
        )

        try:
            await db.update_draft_field(
                int(draft["id"]),
                owner_id,
                "status",
                "published",
            )
        except Exception:
            pass

        return ActionResult(True)

    except Exception as e:
        return ActionResult(False, str(e))