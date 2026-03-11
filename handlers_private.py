from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from actions import create_generated_draft, publish_draft, send_draft_preview, generate_post_payload, generate_hashtags
from config import Config
from db import (
    add_plan_item,
    add_schedule,
    clear_schedules,
    delete_plan_item,
    dm_add_message,
    dm_get_recent,
    get_posts_enabled,
    get_setting,
    list_plan_items,
    list_recent_posts,
    list_schedules,
    set_posts_enabled,
    set_setting,
    get_draft,
    update_draft_field,
    delete_draft,
    get_plan_item,
    update_plan_item,
    upsert_channel_profile,
    list_channel_profiles,
    set_active_channel_profile,
    get_active_channel_profile,
    sync_channel_profile_topic,
    clear_unposted_plan_items,
)
from image_search import find_image
from llm_router import route_message
from news_service import fetch_latest_news, build_news_post
from stats_service import build_channel_stats
from ui_texts import help_text, menu_text, plan_text, schedules_text, status_text, draft_text, news_settings_text


log = logging.getLogger(__name__)
router = Router()
MSK = ZoneInfo("Europe/Moscow")

BTN_MENU = "📌 Меню"
BTN_HELP = "❓ Команды"
BTN_STATUS = "📌 Статус"
BTN_STATS = "📊 Статистика"
BTN_CREATE_POST = "📝 Создать пост"
BTN_OWN_IMAGE = "🖼 Своя картинка"
BTN_SCHEDULE = "🗓️ Расписание"
BTN_PLAN = "📆 Контент-план"
BTN_BIND_CHANNEL = "📣 Привязать канал"
BTN_TOPIC = "🧠 Тема канала"
BTN_NEWS = "📰 Авто-новости"
BTN_RECENT = "📜 Последние посты"
BTN_UPCOMING = "⏭ Ближайшие посты"
BTN_CHANNELS = "🔀 Каналы"

COMMANDISH_RE = re.compile(
    r"^\s*(/|!|канал\b|тема\b|режим\b|запости\b|добав[ьи]\b|удали\b|покажи\b|очист\b|расписан|план\b|стат|авто-новост|свежая новост|источник|интервал новост|тема новост)",
    re.I,
)
DAY_MAP_RU = {
    "пн": "mon", "пон": "mon", "понедельник": "mon",
    "вт": "tue", "втор": "tue", "вторник": "tue",
    "ср": "wed", "сред": "wed", "среда": "wed",
    "чт": "thu", "чет": "thu", "четверг": "thu",
    "пт": "fri", "пят": "fri", "пятница": "fri",
    "сб": "sat", "суб": "sat", "суббота": "sat",
    "вс": "sun", "воск": "sun", "воскресенье": "sun",
}


def main_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_CREATE_POST), KeyboardButton(text=BTN_PLAN)],
        [KeyboardButton(text=BTN_SCHEDULE), KeyboardButton(text=BTN_CHANNELS)],
        [KeyboardButton(text=BTN_BIND_CHANNEL), KeyboardButton(text=BTN_TOPIC)],
        [KeyboardButton(text=BTN_NEWS), KeyboardButton(text=BTN_UPCOMING)],
        [KeyboardButton(text=BTN_RECENT), KeyboardButton(text=BTN_STATS)],
        [KeyboardButton(text=BTN_STATUS), KeyboardButton(text=BTN_HELP)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Выберите действие")


def editor_hint_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CREATE_POST)]],
        resize_keyboard=True,
        input_field_placeholder="Редактор открыт",
    )


def draft_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Текст", callback_data=f"draft:{draft_id}:edit_text"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"draft:{draft_id}:regen"),
            ],
            [
                InlineKeyboardButton(text="🖼 Картинка", callback_data=f"draft:{draft_id}:autoimg"),
                InlineKeyboardButton(text="📷 Своё фото", callback_data=f"draft:{draft_id}:waitphoto"),
            ],
            [InlineKeyboardButton(text="🧹 Убрать фото", callback_data=f"draft:{draft_id}:clearimg")],
            [
                InlineKeyboardButton(text="🔘 Кнопка", callback_data=f"draft:{draft_id}:addbtn"),
                InlineKeyboardButton(text="🧽 Очистить", callback_data=f"draft:{draft_id}:clearbtn"),
            ],
            [
                InlineKeyboardButton(text="🏷 Хештеги", callback_data=f"draft:{draft_id}:hashtags"),
                InlineKeyboardButton(text="📌 Закреп", callback_data=f"draft:{draft_id}:pin"),
            ],
            [InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"draft:{draft_id}:preview")],
            [
                InlineKeyboardButton(text="⏰ Отложить", callback_data=f"draft:{draft_id}:schedule"),
                InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"draft:{draft_id}:publish"),
            ],
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"draft:{draft_id}:delete")],
        ]
    )


def news_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    toggle = "Выключить" if enabled else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔄 {toggle}", callback_data="news:toggle"),
                InlineKeyboardButton(text="✏️ Тема", callback_data="news:topic"),
            ],
            [
                InlineKeyboardButton(text="⏱ Интервал", callback_data="news:interval"),
                InlineKeyboardButton(text="🌍 Источники", callback_data="news:sources"),
            ],
            [InlineKeyboardButton(text="📰 Пост сейчас", callback_data="news:postnow")],
        ]
    )


def channels_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        prefix = "✅" if int(item.get("is_active", 0)) else "▫️"
        label = f"{prefix} {(item.get('title') or item.get('channel_target') or 'канал')[:32]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"channel:set:{item['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Пока нет каналов", callback_data="channel:none")]])


async def _show_channels(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    items = await list_channel_profiles(owner_id=user_id)
    if not items:
        await message.answer("🔀 КАНАЛЫ\n\nПока нет сохранённых каналов.\nПривяжи канал командой: канал @username", reply_markup=main_keyboard())
        return
    active = next((x for x in items if int(x.get('is_active', 0)) == 1), None)
    lines = ["🔀 КАНАЛЫ", ""]
    if active:
        lines.append(f"Активный: {active.get('title') or active.get('channel_target')}")
        if active.get('topic'):
            lines.append(f"Тема: {active.get('topic')}")
        lines.append("")
    lines.append("Выбери канал:")
    await message.answer("\n".join(lines), reply_markup=channels_keyboard(items))


_HASHTAG_RE = re.compile(r"(?:\n\n|\n)?(?:#[\w\d_]+(?:\s+#[\w\d_]+)*)\s*$", re.I)


def _replace_hashtags(text: str, tags_line: str) -> str:
    base = (text or "").rstrip()
    base = re.sub(_HASHTAG_RE, "", base).rstrip()
    tags_line = (tags_line or "").strip()
    if not tags_line:
        return base
    return f"{base}\n\n{tags_line}"


def _normalize_plan_topic(raw: str, fallback_topic: str = "") -> str:
    text = (raw or "").strip()
    if not text:
        return (fallback_topic or "контент канала").strip() or "контент канала"

    explicit_patterns = [
        r"(?:на тему|по теме)\s+(.+)$",
        r"\bпро\s+(.+)$",
    ]
    for pattern in explicit_patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            candidate = m.group(1).strip(" .,:;!?")
            if candidate:
                return candidate

    cleaned = text
    cleaned = re.sub(r"^(придумай|сделай|сформируй|составь|создай)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"контент\s*[- ]?план", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bна\s+(?:текущ(?:ий|ую)|эт(?:от|у))?\s*месяц\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bна\s+(?:текущ(?:ую)|эт(?:у))?\s*недел[юе]\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bна\s+\d+\s*(?:дн(?:я|ей)?|сут(?:ок|ки)?)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bна\s+сегодня\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bна\s+завтра\b", "", cleaned, flags=re.I)
    cleaned = cleaned.strip(" .,:;!?")
    if cleaned and len(cleaned) >= 3:
        return cleaned
    return (fallback_topic or "контент канала").strip() or "контент канала"


def _generate_plan_title(topic: str, idx: int, total: int) -> str:
    base = (topic or "контент канала").strip()
    templates = [
        "Главная польза для аудитории в теме: {topic}",
        "3 частые ошибки в теме: {topic}",
        "Пошаговый мини-гайд по теме: {topic}",
        "Разбор кейса / примера по теме: {topic}",
        "Мифы и правда в теме: {topic}",
        "Подборка советов по теме: {topic}",
        "Ответы на частые вопросы по теме: {topic}",
        "Что важно сделать уже сегодня по теме: {topic}",
        "Чек-лист для новичка по теме: {topic}",
        "Главные ошибки, которые мешают результату в теме: {topic}",
    ]
    if total >= 20:
        weekday_templates = [
            "План на день: что важно знать по теме {topic}",
            "Практический совет дня по теме: {topic}",
            "Мини-разбор для подписчиков по теме: {topic}",
            "Полезная привычка дня в теме: {topic}",
            "Ответ на популярный вопрос по теме: {topic}",
            "Идея поста дня по теме: {topic}",
            "Что чаще всего недооценивают в теме: {topic}",
        ]
        templates = weekday_templates + templates
    return templates[idx % len(templates)].format(topic=base)


def _generate_period_plan_items(topic: str, start_date, end_date, post_time=(10, 0), current_dt: datetime | None = None) -> list[tuple[str, str]]:
    base = (topic or "контент канала").strip()
    now_dt = current_dt or datetime.now(MSK)
    out = []
    cur = start_date
    total = (end_date - start_date).days + 1
    idx = 0
    while cur <= end_date:
        dt = cur.replace(hour=post_time[0], minute=post_time[1], second=0, microsecond=0)
        if dt <= now_dt and cur.date() == now_dt.date():
            dt = (now_dt + timedelta(minutes=5)).replace(second=0, microsecond=0)
        out.append((dt.strftime("%Y-%m-%d %H:%M"), _generate_plan_title(base, idx, total)))
        idx += 1
        cur = cur + timedelta(days=1)
    return out


def _month_range(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end = next_month - timedelta(days=1)
    return start, end


def _parse_plan_generation_request(raw: str) -> tuple[bool, datetime | None, datetime | None, str]:
    low = (raw or "").lower()
    if "контент" not in low or "план" not in low:
        return False, None, None, ""
    if not any(w in low for w in ["придум", "сдел", "сформ", "состав", "созд"]):
        return False, None, None, ""

    now = datetime.now(MSK)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if re.search(r"\b(?:на\s+)?(?:текущ(?:ий|ую)|эт(?:от|у))?\s*месяц\b", low):
        month_start, month_end = _month_range(now)
        return True, month_start, month_end, "текущий месяц"

    if re.search(r"\b(?:на\s+)?(?:текущ(?:ую)|эт(?:у))?\s*недел[юе]\b", low):
        return True, start, start + timedelta(days=6), "текущую неделю"

    m = re.search(r"\b(?:на\s+)?(\d+)\s*(дн(?:я|ей)?|сут(?:ок|ки)?)\b", low)
    if m:
        days = max(1, int(m.group(1)))
        end = start + timedelta(days=days - 1)
        if days % 10 == 1 and days % 100 != 11:
            word = "день"
        elif days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14):
            word = "дня"
        else:
            word = "дней"
        return True, start, end, f"{days} {word}"

    if "сегодня" in low:
        return True, start, start, "сегодня"
    if "завтра" in low:
        tomorrow = start + timedelta(days=1)
        return True, tomorrow, tomorrow, "завтра"

    return False, None, None, ""


async def _generate_period_plan(message: Message, scheduler, topic: str, *, start_date: datetime, end_date: datetime, label: str, clear_existing: bool = True):
    user_id = message.from_user.id if message.from_user else 0
    active = await get_active_channel_profile(owner_id=user_id)
    fallback_topic = (await get_setting("topic", owner_id=user_id) or "").strip()
    if not fallback_topic and active:
        fallback_topic = (active.get("topic") or "").strip()
    topic = (topic or fallback_topic or "контент канала").strip()

    now = datetime.now(MSK)
    if clear_existing:
        await clear_unposted_plan_items(owner_id=user_id)

    items = _generate_period_plan_items(topic, start_date, end_date, current_dt=now)
    for dt, title in items:
        await add_plan_item(dt=dt, topic=title, owner_id=user_id)

    if scheduler:
        await scheduler.rebuild_jobs()

    count = len(items)
    await message.answer(
        f"✅ Сформировал контент-план на {label}: {count} публикаций по теме: {topic}.\n\n"
        + plan_text(await list_plan_items(limit=120, owner_id=user_id))
        + "\n\n" + _plan_edit_help(),
        reply_markup=main_keyboard(),
    )


def _is_plan_generation_request(low: str) -> tuple[bool, str]:
    ok, _start, _end, label = _parse_plan_generation_request(low)
    return ok, label


def _plan_edit_help() -> str:
    return (
        "Редактирование плана:\n"
        "• редактировать план 12 тема: Новый заголовок\n"
        "• редактировать план 12 дата: 2026-03-25 18:30\n"
        "• удалить запись 12"
    )


def _is_admin(message: Message, config: Config) -> bool:
    uid = message.from_user.id if message.from_user else 0
    return uid in set(config.admin_ids)


async def _remember(user_id: int, role: str, text: str) -> None:
    text = (text or "").strip()
    if text:
        await dm_add_message(user_id, role=role, text=text)


async def _ctx(message: Message, config: Config) -> dict:
    user_id = message.from_user.id if message.from_user else 0
    history = await dm_get_recent(user_id, limit=14)
    return {
        "user_id": user_id,
        "is_admin": _is_admin(message, config),
        "channel": await get_setting("channel_target", owner_id=user_id) or "",
        "topic": await get_setting("topic", owner_id=user_id) or "",
        "posts_enabled": await get_posts_enabled(owner_id=user_id),
        "posting_mode": await get_setting("posting_mode", owner_id=user_id) or "both",
        "bound_chat": str(message.chat.id),
        "dm_history": [{"role": h["role"], "text": h["text"]} for h in history],
    }


async def _send_status(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    news_enabled = (await get_setting("news_enabled", owner_id=user_id) or "0").strip() not in ("0", "false", "False")
    await message.answer(
        status_text(
            channel=await get_setting("channel_target", owner_id=user_id),
            topic=await get_setting("topic", owner_id=user_id),
            posts_enabled=await get_posts_enabled(owner_id=user_id),
            posting_mode=await get_setting("posting_mode", owner_id=user_id) or "both",
            bound_chat=str(message.chat.id),
            news_enabled=news_enabled,
        ),
        reply_markup=main_keyboard(),
    )


async def _send_stats(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    txt = await build_channel_stats(message.bot, owner_id=user_id)
    await message.answer(txt, reply_markup=main_keyboard())


async def _send_recent_posts(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    posts = await list_recent_posts(owner_id=user_id, limit=7)
    if not posts:
        await message.answer("Пока нет опубликованных постов.", reply_markup=main_keyboard())
        return
    lines = ["📜 ПОСЛЕДНИЕ ПОСТЫ", ""]
    for p in posts:
        label = (p.get("topic") or p.get("prompt") or p.get("text") or "").replace("\n", " ").strip()
        if len(label) > 80:
            label = label[:77] + "..."
        lines.append(f"• {p.get('created_at', '')} — {label}")
    await message.answer("\n".join(lines), reply_markup=main_keyboard())


async def _send_upcoming_posts(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    items = await list_plan_items(limit=20, owner_id=user_id)
    future = [x for x in items if not int(x.get("posted", 0))]
    if not future:
        await message.answer("Нет запланированных публикаций.", reply_markup=main_keyboard())
        return
    lines = ["⏭ БЛИЖАЙШИЕ ПУБЛИКАЦИИ", ""]
    for p in future[:7]:
        label = "черновик" if p.get("kind") == "draft" else (p.get("topic") or p.get("prompt") or p.get("payload") or "").strip()
        if len(label) > 80:
            label = label[:77] + "..."
        lines.append(f"• {p.get('dt', '')} — {label}")
    await message.answer("\n".join(lines), reply_markup=main_keyboard())


def _ru_days_to_cron(s: str) -> str:
    t = (s or "").lower().strip()
    if not t or "каждый день" in t or t == "каждый" or t == "ежедневно":
        return "*"
    if "будн" in t:
        return "mon,tue,wed,thu,fri"
    if "выходн" in t:
        return "sat,sun"
    parts = re.split(r"[,\s]+", t)
    out = []
    for p in parts:
        if p in DAY_MAP_RU:
            out.append(DAY_MAP_RU[p])
    uniq = list(dict.fromkeys(out))
    return ",".join(uniq) if uniq else "*"


def _extract_prompt(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^(запости|сделай|выложи)\s+", "", t, flags=re.I)
    t = re.sub(r"^пост\s+", "", t, flags=re.I)
    t = re.sub(r"^с картинкой\s+", "", t, flags=re.I)
    t = re.sub(r"^без картинки\s+", "", t, flags=re.I)
    t = re.sub(r"^(про|на тему)\s+", "", t, flags=re.I)
    return t.strip(" :,-")


async def _show_draft(message_or_callback, draft_id: int, owner_id: int):
    draft = await get_draft(draft_id, owner_id=owner_id)
    if not draft:
        txt = "Черновик не найден."
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer(txt, show_alert=True)
        else:
            await message_or_callback.answer(txt, reply_markup=main_keyboard())
        return
    txt = draft_text(draft)
    kb = draft_keyboard(draft_id)
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.answer("🎛 Редактор открыт. Основные действия — под черновиком.", reply_markup=editor_hint_keyboard())
        await message_or_callback.message.answer(txt, reply_markup=kb)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer("🎛 Редактор открыт. Основные действия — под черновиком.", reply_markup=editor_hint_keyboard())
        await message_or_callback.answer(txt, reply_markup=kb)


async def _show_news_settings(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    enabled = (await get_setting("news_enabled", owner_id=user_id) or "0").strip() not in ("0", "false", "False")
    topic = (await get_setting("news_topic", owner_id=user_id) or "").strip()
    interval = int((await get_setting("news_interval_hours", owner_id=user_id) or "6").strip() or "6")
    sources = (await get_setting("news_sources", owner_id=user_id) or "").strip()
    await message.answer(news_settings_text(enabled, topic, interval, sources), reply_markup=news_keyboard(enabled))


async def _set_editor_mode(user_id: int, mode: str):
    await set_setting("editor_mode", mode, owner_id=user_id)


async def _clear_editor_mode(user_id: int):
    await set_setting("editor_mode", "", owner_id=user_id)


@router.message(Command("start"))
async def cmd_start(message: Message, config: Config):
    user_id = message.from_user.id if message.from_user else 0
    txt = "Привет! Нажимай кнопки или пиши обычным текстом — я понимаю по смыслу."
    await message.answer(txt, reply_markup=main_keyboard())
    if user_id:
        await _remember(user_id, "assistant", txt)


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(menu_text(), reply_markup=main_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message, config: Config):
    await message.answer(help_text(is_admin=_is_admin(message, config)), reply_markup=main_keyboard())


@router.message(Command("status"))
async def cmd_status(message: Message):
    await _send_status(message)


@router.callback_query(F.data.startswith("draft:"))
async def draft_callback(call: CallbackQuery, config: Config, scheduler):
    user_id = call.from_user.id if call.from_user else 0
    try:
        _, draft_id_s, action = (call.data or "").split(":", 2)
        draft_id = int(draft_id_s)
    except Exception:
        await call.answer("Неверная команда")
        return

    draft = await get_draft(draft_id, owner_id=user_id)
    if not draft:
        await call.answer("Черновик не найден", show_alert=True)
        return

    if action == "edit_text":
        await _set_editor_mode(user_id, f"edit_text:{draft_id}")
        await call.message.answer("Пришли новый текст для поста.")
        await call.answer()
        return

    if action == "regen":
        payload = await generate_post_payload(
            config,
            draft.get("prompt") or draft.get("topic") or "",
            owner_id=user_id,
            force_image=(draft.get("media_type") == "photo"),
        )
        await update_draft_field(draft_id, user_id, "text", payload["text"])
        if payload["media_ref"]:
            await update_draft_field(draft_id, user_id, "media_type", "photo")
            await update_draft_field(draft_id, user_id, "media_ref", payload["media_ref"])
        await _show_draft(call, draft_id, user_id)
        return

    if action == "autoimg":
        prompt = draft.get("prompt") or draft.get("topic") or draft.get("text")[:120]
        image_ref = await find_image(prompt)
        if image_ref:
            await update_draft_field(draft_id, user_id, "media_type", "photo")
            await update_draft_field(draft_id, user_id, "media_ref", image_ref)
            await call.message.answer("✅ Новая картинка найдена.")
        else:
            await call.message.answer("Не удалось найти картинку.")
        await _show_draft(call, draft_id, user_id)
        return

    if action == "waitphoto":
        await _set_editor_mode(user_id, f"replace_photo:{draft_id}")
        await call.message.answer("Отправь фото, и я заменю картинку в черновике.")
        await call.answer()
        return

    if action == "clearimg":
        await update_draft_field(draft_id, user_id, "media_type", "none")
        await update_draft_field(draft_id, user_id, "media_ref", "")
        await _show_draft(call, draft_id, user_id)
        return

    if action == "addbtn":
        await _set_editor_mode(user_id, f"add_button:{draft_id}")
        await call.message.answer("Пришли кнопку в формате:\nТекст | https://example.com")
        await call.answer()
        return

    if action == "clearbtn":
        await update_draft_field(draft_id, user_id, "buttons_json", "[]")
        await _show_draft(call, draft_id, user_id)
        return

    if action == "hashtags":
        tags_line = generate_hashtags(draft.get("topic") or draft.get("prompt") or "", draft.get("text") or "")
        if not tags_line:
            await call.message.answer("Не удалось подобрать хештеги.")
            await call.answer()
            return
        new_text = _replace_hashtags(draft.get("text") or "", tags_line)
        await update_draft_field(draft_id, user_id, "text", new_text)
        await call.message.answer("✅ Хештеги добавлены в конец поста.")
        await _show_draft(call, draft_id, user_id)
        return

    if action == "pin":
        new_value = 0 if int(draft.get("pin_post", 0)) else 1
        await update_draft_field(draft_id, user_id, "pin_post", new_value)
        await _show_draft(call, draft_id, user_id)
        return

    if action == "preview":
        await send_draft_preview(call.message, call.message.bot, draft, owner_id=user_id)
        await call.answer("Предпросмотр отправлен")
        return

    if action == "schedule":
        await _set_editor_mode(user_id, f"schedule_draft:{draft_id}")
        await call.message.answer("Пришли дату и время в формате:\n2026-03-12 18:30")
        await call.answer()
        return

    if action == "publish":
        res = await publish_draft(call.message.bot, draft, owner_id=user_id)
        await call.message.answer("✅ Опубликовано." if res.ok else f"❌ Ошибка: {res.error}", reply_markup=main_keyboard())
        await call.answer()
        return

    if action == "delete":
        await delete_draft(draft_id, owner_id=user_id)
        await call.message.answer("🗑 Черновик удалён.", reply_markup=main_keyboard())
        await call.answer()
        return

    await call.answer("Неизвестное действие")


@router.callback_query(F.data.startswith("channel:"))
async def channel_callback(call: CallbackQuery):
    user_id = call.from_user.id if call.from_user else 0
    data = (call.data or "").split(":")
    if len(data) < 2:
        await call.answer("Неверная команда")
        return
    action = data[1]
    if action == "none":
        await call.answer()
        return
    if action == "set" and len(data) >= 3:
        try:
            profile_id = int(data[2])
        except Exception:
            await call.answer("Неверный id")
            return
        profile = await set_active_channel_profile(profile_id, owner_id=user_id)
        if not profile:
            await call.answer("Канал не найден", show_alert=True)
            return
        await call.message.answer(f"✅ Активный канал: {profile.get('title') or profile.get('channel_target')}", reply_markup=main_keyboard())
        await call.answer("Канал переключён")
        return
    await call.answer("Неизвестное действие")


@router.callback_query(F.data.startswith("news:"))
async def news_callback(call: CallbackQuery, config: Config):
    user_id = call.from_user.id if call.from_user else 0
    action = (call.data or "").split(":", 1)[1]

    if action == "toggle":
        enabled = (await get_setting("news_enabled", owner_id=user_id) or "0").strip() not in ("0", "false", "False")
        await set_setting("news_enabled", "0" if enabled else "1", owner_id=user_id)
        await call.answer("Готово")
        await _show_news_settings(call.message)
        return

    if action == "topic":
        await _set_editor_mode(user_id, "news_topic")
        await call.message.answer("Пришли новую тему новостей.")
        await call.answer()
        return

    if action == "interval":
        await _set_editor_mode(user_id, "news_interval")
        await call.message.answer("Пришли интервал в часах. Пример: 6")
        await call.answer()
        return

    if action == "sources":
        await _set_editor_mode(user_id, "news_sources")
        await call.message.answer("Пришли источники через запятую.\nПример: who.int, mayoclinic.org, nih.gov")
        await call.answer()
        return

    if action == "postnow":
        item = await fetch_latest_news(owner_id=user_id)
        if not item:
            await call.message.answer("Не нашёл свежую новость по текущей теме.")
            await call.answer()
            return

        text = await build_news_post(config, item, owner_id=user_id)
        draft_id = await create_generated_draft(
            config,
            item.get("title") or item.get("topic") or "",
            owner_id=user_id,
            force_image=True,
        )
        await update_draft_field(draft_id, user_id, "text", text)
        await update_draft_field(draft_id, user_id, "topic", item.get("topic", ""))
        await update_draft_field(draft_id, user_id, "prompt", item.get("title", ""))
        if item.get("image_url"):
            await update_draft_field(draft_id, user_id, "media_type", "photo")
            await update_draft_field(draft_id, user_id, "media_ref", item["image_url"])

        await call.message.answer("Создал черновик новости:")
        await _show_draft(call, draft_id, user_id)
        return


@router.message(F.chat.type == "private", F.photo)
async def handle_private_photo(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not message.photo:
        return
    photo = message.photo[-1]
    mode = (await get_setting("editor_mode", owner_id=user_id) or "").strip()

    if mode.startswith("replace_photo:"):
        try:
            draft_id = int(mode.split(":", 1)[1])
            await update_draft_field(draft_id, user_id, "media_type", "photo")
            await update_draft_field(draft_id, user_id, "media_ref", photo.file_id)
            await _clear_editor_mode(user_id)
            await message.answer("✅ Картинка заменена.")
            await _show_draft(message, draft_id, user_id)
            return
        except Exception:
            pass

    await set_setting("pending_image_file_id", photo.file_id, owner_id=user_id)
    await _set_editor_mode(user_id, "new_post_with_own_image")
    await message.answer("✅ Фото получил. Теперь напиши тему или идею поста.", reply_markup=main_keyboard())


async def _try_local_parse(message: Message, scheduler, config: Config, raw: str) -> bool:
    user_id = message.from_user.id if message.from_user else 0
    low = raw.lower().strip()

    mode = (await get_setting("editor_mode", owner_id=user_id) or "").strip()
    if mode:
        if mode.startswith("edit_text:"):
            draft_id = int(mode.split(":", 1)[1])
            await update_draft_field(draft_id, user_id, "text", raw)
            await _clear_editor_mode(user_id)
            await message.answer("✅ Текст обновлён.")
            await _show_draft(message, draft_id, user_id)
            return True

        if mode.startswith("add_button:"):
            draft_id = int(mode.split(":", 1)[1])
            parts = [p.strip() for p in raw.split("|", 1)]
            if len(parts) != 2 or not parts[0] or not parts[1].startswith(("http://", "https://")):
                await message.answer("Нужен формат:\nТекст | https://example.com")
                return True
            draft = await get_draft(draft_id, owner_id=user_id)
            arr = []
            try:
                arr = json.loads(draft.get("buttons_json") or "[]") if draft else []
            except Exception:
                arr = []
            arr.append({"text": parts[0], "url": parts[1]})
            await update_draft_field(draft_id, user_id, "buttons_json", json.dumps(arr, ensure_ascii=False))
            await _clear_editor_mode(user_id)
            await message.answer("✅ Кнопка добавлена.")
            await _show_draft(message, draft_id, user_id)
            return True

        if mode.startswith("schedule_draft:"):
            draft_id = int(mode.split(":", 1)[1])
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}", raw.strip()):
                await message.answer("Нужен формат:\n2026-03-12 18:30")
                return True
            await add_plan_item(raw.strip(), kind="draft", payload=str(draft_id), owner_id=user_id)
            await update_draft_field(draft_id, user_id, "status", "scheduled")
            if scheduler:
                await scheduler.rebuild_jobs()
            await _clear_editor_mode(user_id)
            await message.answer("✅ Черновик отложен и добавлен в контент-план.", reply_markup=main_keyboard())
            return True

        if mode == "news_topic":
            await set_setting("news_topic", raw.strip(), owner_id=user_id)
            await _clear_editor_mode(user_id)
            await message.answer("✅ Тема новостей обновлена.")
            await _show_news_settings(message)
            return True

        if mode == "news_interval":
            m = re.search(r"(\d+)", raw)
            if not m:
                await message.answer("Пришли число часов, например: 6")
                return True
            await set_setting("news_interval_hours", m.group(1), owner_id=user_id)
            await _clear_editor_mode(user_id)
            await message.answer("✅ Интервал новостей обновлён.")
            await _show_news_settings(message)
            return True

        if mode == "news_sources":
            await set_setting("news_sources", raw.strip(), owner_id=user_id)
            await _clear_editor_mode(user_id)
            await message.answer("✅ Источники новостей обновлены.")
            await _show_news_settings(message)
            return True

        if mode == "new_post_with_own_image":
            prompt = raw.strip()
            pending_photo = (await get_setting("pending_image_file_id", owner_id=user_id) or "").strip()
            if not pending_photo:
                await message.answer("Сначала пришли фото.")
                return True
            draft_id = await create_generated_draft(config, prompt, owner_id=user_id, force_image=False)
            await update_draft_field(draft_id, user_id, "media_type", "photo")
            await update_draft_field(draft_id, user_id, "media_ref", pending_photo)
            await set_setting("pending_image_file_id", "", owner_id=user_id)
            await _clear_editor_mode(user_id)
            await message.answer("Создал черновик с твоей картинкой:")
            await _show_draft(message, draft_id, user_id)
            return True

    if low in (BTN_MENU.lower(), "меню"):
        await message.answer(menu_text(), reply_markup=main_keyboard())
        return True
    if low in (BTN_HELP.lower(), "команды", "что ты умеешь"):
        await message.answer(help_text(is_admin=_is_admin(message, config)), reply_markup=main_keyboard())
        return True
    if low in (BTN_STATUS.lower(), "статус", "покажи статус"):
        await _send_status(message)
        return True
    if low in (BTN_STATS.lower(), "статистика", "стата", "статистика канала", "покажи статистику"):
        await _send_stats(message)
        return True
    if low in (BTN_RECENT.lower(), "последние посты", "история постов"):
        await _send_recent_posts(message)
        return True
    if low in (BTN_UPCOMING.lower(), "ближайшие посты", "что выйдет", "что выйдет сегодня"):
        await _send_upcoming_posts(message)
        return True
    if low in (BTN_SCHEDULE.lower(), "расписание"):
        await message.answer(schedules_text(await list_schedules(owner_id=user_id)), reply_markup=main_keyboard())
        return True
    if low in (BTN_PLAN.lower(), "контент-план", "контент план"):
        await message.answer(plan_text(await list_plan_items(limit=80, owner_id=user_id)) + "\n\n" + _plan_edit_help(), reply_markup=main_keyboard())
        return True

    is_plan_request, _plan_label = _is_plan_generation_request(low)
    if is_plan_request:
        ok, start_date, end_date, label = _parse_plan_generation_request(raw)
        active = await get_active_channel_profile(owner_id=user_id)
        fallback_topic = (await get_setting("topic", owner_id=user_id) or "").strip()
        if not fallback_topic and active:
            fallback_topic = (active.get("topic") or "").strip()
        topic = _normalize_plan_topic(raw, fallback_topic=fallback_topic)
        await _generate_period_plan(message, scheduler, topic, start_date=start_date, end_date=end_date, label=label, clear_existing=True)
        return True
    if low in (BTN_BIND_CHANNEL.lower(), "привязать канал"):
        await message.answer("Напиши: канал @username или канал -1001234567890", reply_markup=main_keyboard())
        return True
    if low in (BTN_CHANNELS.lower(), "каналы", "смена канала", "переключить канал"):
        await _show_channels(message)
        return True
    if low in (BTN_TOPIC.lower(), "тема канала"):
        await message.answer("Напиши: тема: ...", reply_markup=main_keyboard())
        return True
    if low in (BTN_CREATE_POST.lower(), "создать пост"):
        await message.answer("Напиши тему поста. Я создам черновик и открою редактор.", reply_markup=main_keyboard())
        await _set_editor_mode(user_id, "create_post")
        return True
    if low in (BTN_NEWS.lower(), "авто-новости"):
        await _show_news_settings(message)
        return True

    m = re.search(r"(?:^|\b)канал\s+(@[\w\d_]{3,}|-100\d+)\b", raw, flags=re.I)
    if m:
        ref = m.group(1).strip()
        current_topic = (await get_setting("topic", owner_id=user_id) or "").strip()
        await set_setting("channel_target", ref, owner_id=user_id)
        await upsert_channel_profile(user_id, ref, title=ref, topic=current_topic, make_active=True)
        await message.answer(f"✅ Канал установлен: {ref}", reply_markup=main_keyboard())
        return True

    m = re.search(r"(?:^|\b)тема\s*:?\s*(.+)$", raw, flags=re.I)
    if m and low.startswith("тема"):
        topic = m.group(1).strip()
        if topic:
            await set_setting("topic", topic, owner_id=user_id)
            channel_target = await get_setting("channel_target", owner_id=user_id) or ""
            if channel_target:
                await sync_channel_profile_topic(user_id, channel_target, topic)
            await message.answer(f"✅ Тема сохранена: {topic}", reply_markup=main_keyboard())
            return True

    if "авто-новости включить" in low:
        await set_setting("news_enabled", "1", owner_id=user_id)
        await message.answer("✅ Авто-новости включены.", reply_markup=main_keyboard())
        await _show_news_settings(message)
        return True
    if "авто-новости выключить" in low:
        await set_setting("news_enabled", "0", owner_id=user_id)
        await message.answer("⛔ Авто-новости выключены.", reply_markup=main_keyboard())
        await _show_news_settings(message)
        return True
    m = re.search(r"тема новостей\s*:?\s*(.+)$", raw, flags=re.I)
    if m:
        await set_setting("news_topic", m.group(1).strip(), owner_id=user_id)
        await message.answer("✅ Тема новостей сохранена.", reply_markup=main_keyboard())
        return True
    m = re.search(r"интервал новостей\s*:?\s*(\d+)", raw, flags=re.I)
    if m:
        await set_setting("news_interval_hours", m.group(1), owner_id=user_id)
        await message.answer("✅ Интервал новостей сохранён.", reply_markup=main_keyboard())
        return True
    m = re.search(r"источники новостей\s*:?\s*(.+)$", raw, flags=re.I)
    if m:
        await set_setting("news_sources", m.group(1).strip(), owner_id=user_id)
        await message.answer("✅ Источники новостей сохранены.", reply_markup=main_keyboard())
        return True

    if low == "свежая новость":
        item = await fetch_latest_news(owner_id=user_id)
        if not item:
            await message.answer("Не нашёл свежую новость по текущей теме.", reply_markup=main_keyboard())
            return True
        text = await build_news_post(config, item, owner_id=user_id)
        draft_id = await create_generated_draft(
            config,
            item.get("title") or item.get("topic") or "",
            owner_id=user_id,
            force_image=True,
        )
        await update_draft_field(draft_id, user_id, "text", text)
        await update_draft_field(draft_id, user_id, "topic", item.get("topic", ""))
        await update_draft_field(draft_id, user_id, "prompt", item.get("title", ""))
        if item.get("image_url"):
            await update_draft_field(draft_id, user_id, "media_type", "photo")
            await update_draft_field(draft_id, user_id, "media_ref", item["image_url"])
        await message.answer("Создал черновик новости:")
        await _show_draft(message, draft_id, user_id)
        return True

    if low.startswith("добавь расписание") or low.startswith("добавить расписание"):
        m = re.search(r"(\d{1,2}:\d{2})(.*)$", low)
        if not m:
            await message.answer("Пример: добавь расписание 10:30 пн ср пт", reply_markup=main_keyboard())
            return True
        hhmm = m.group(1)
        days = _ru_days_to_cron(m.group(2))
        await add_schedule(hhmm, days, owner_id=user_id)
        if scheduler:
            await scheduler.rebuild_jobs()
        await message.answer("✅ Добавил.\n" + schedules_text(await list_schedules(owner_id=user_id)), reply_markup=main_keyboard())
        return True

    if low.startswith("очисти расписание"):
        await clear_schedules(owner_id=user_id)
        if scheduler:
            await scheduler.rebuild_jobs()
        await message.answer("✅ Расписание очищено.", reply_markup=main_keyboard())
        return True


    m = re.search(r"добав[ьи]\s+в\s+план\s+(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s*(.*)$", raw, flags=re.I)
    if m:
        dt = f"{m.group(1)} {m.group(2)}"
        tail = m.group(3).strip()
        topic = ""
        prompt = ""
        mm = re.search(r"тема\s*:\s*(.+)$", tail, flags=re.I)
        if mm:
            topic = mm.group(1).strip()
        mm = re.search(r"промпт\s*:\s*(.+)$", tail, flags=re.I)
        if mm:
            prompt = mm.group(1).strip()
        if topic or prompt:
            await add_plan_item(dt=dt, topic=topic, prompt=prompt, owner_id=user_id)
            if scheduler:
                await scheduler.rebuild_jobs()
            await message.answer("✅ Добавил в контент-план.\n" + plan_text(await list_plan_items(limit=80, owner_id=user_id)), reply_markup=main_keyboard())
            return True

    m = re.search(r"(?:редактируй|редактировать|измени|изменить)\s+план\s+(\d+)\s+(.*)$", raw, flags=re.I)
    if m:
        item_id = int(m.group(1))
        tail = (m.group(2) or "").strip()
        item = await get_plan_item(item_id, owner_id=user_id)
        if not item:
            await message.answer("Не нашёл такую запись в контент-плане.", reply_markup=main_keyboard())
            return True
        mm = re.search(r"дата\s*:\s*(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})", tail, flags=re.I)
        if mm:
            await update_plan_item(item_id, owner_id=user_id, dt=mm.group(1).strip())
            if scheduler:
                await scheduler.rebuild_jobs()
            await message.answer("✅ Дата записи обновлена.\n" + plan_text(await list_plan_items(limit=80, owner_id=user_id)), reply_markup=main_keyboard())
            return True
        mm = re.search(r"(?:тема|заголовок|текст)\s*:\s*(.+)$", tail, flags=re.I)
        if mm:
            await update_plan_item(item_id, owner_id=user_id, topic=mm.group(1).strip())
            if scheduler:
                await scheduler.rebuild_jobs()
            await message.answer("✅ Тема записи обновлена.\n" + plan_text(await list_plan_items(limit=80, owner_id=user_id)), reply_markup=main_keyboard())
            return True
        await message.answer(_plan_edit_help(), reply_markup=main_keyboard())
        return True

    if re.search(r"(?:удали|удалить|очисти|очистить)\s+(?:весь\s+)?контент\s*[- ]?план", low, flags=re.I):
        await clear_unposted_plan_items(owner_id=user_id)
        if scheduler:
            await scheduler.rebuild_jobs()
        await message.answer("✅ Контент-план очищен.\n" + plan_text(await list_plan_items(limit=120, owner_id=user_id)), reply_markup=main_keyboard())
        return True

    m = re.search(r"(?:удали|удалить)\s+(?:пост|запись)\s+(\d+)", low)
    if m:
        await delete_plan_item(int(m.group(1)), owner_id=user_id)
        if scheduler:
            await scheduler.rebuild_jobs()
        await message.answer("✅ Удалил.\n" + plan_text(await list_plan_items(limit=80, owner_id=user_id)), reply_markup=main_keyboard())
        return True

    m = re.search(r"через\s+(\d+)\s*(мин|минут|час|часа|часов|день|дня|дней)\s*(.*)$", low)
    if m:
        value = int(m.group(1))
        unit = m.group(2)
        tail = m.group(3).strip()
        now = datetime.now(MSK)
        if "час" in unit:
            dt = now + timedelta(hours=value)
        elif "дн" in unit:
            dt = now + timedelta(days=value)
        else:
            dt = now + timedelta(minutes=value)
        prompt = _extract_prompt(tail)
        if not prompt:
            prompt = await get_setting("topic", owner_id=user_id) or "пост"
        draft_id = await create_generated_draft(config, prompt, owner_id=user_id, force_image=("без картинки" not in low and "только текст" not in low))
        await add_plan_item(dt.strftime("%Y-%m-%d %H:%M"), kind="draft", payload=str(draft_id), owner_id=user_id)
        await update_draft_field(draft_id, user_id, "status", "scheduled")
        if scheduler:
            await scheduler.rebuild_jobs()
        await message.answer(f"⏳ Создал черновик и запланировал публикацию на {dt.strftime('%Y-%m-%d %H:%M')} (МСК).", reply_markup=main_keyboard())
        await _show_draft(message, draft_id, user_id)
        return True

    m = re.search(r"каждые\s+(\d+)\s*дн(?:я|ей)?\s*(.*)$", low)
    if m:
        step = int(m.group(1))
        tail = m.group(2).strip()
        prompt = _extract_prompt(tail) or (await get_setting("topic", owner_id=user_id) or "пост")
        start = datetime.now(MSK)
        for i in range(6):
            draft_id = await create_generated_draft(config, prompt, owner_id=user_id, force_image=("без картинки" not in low and "только текст" not in low))
            dt = start + timedelta(days=step * i)
            await add_plan_item(dt.strftime("%Y-%m-%d %H:%M"), kind="draft", payload=str(draft_id), owner_id=user_id)
            await update_draft_field(draft_id, user_id, "status", "scheduled")
        if scheduler:
            await scheduler.rebuild_jobs()
        await message.answer(f"🔁 Создал серию из 6 черновиков каждые {step} дн.", reply_markup=main_keyboard())
        return True

    if mode == "create_post":
        prompt = _extract_prompt(raw) or raw.strip()
        draft_id = await create_generated_draft(config, prompt, owner_id=user_id, force_image=("без картинки" not in low and "только текст" not in low))
        await _clear_editor_mode(user_id)
        await message.answer("Создал черновик:")
        await _show_draft(message, draft_id, user_id)
        return True

    if any(k in low for k in ["пост", "запости", "выложи", "сделай"]) and not low.startswith("добавь ") and not low.startswith("удали "):
        prompt = _extract_prompt(raw) or raw
        force_image = not ("без картинки" in low or "только текст" in low)
        draft_id = await create_generated_draft(config, prompt, owner_id=user_id, force_image=force_image)
        await message.answer("Создал черновик:")
        await _show_draft(message, draft_id, user_id)
        return True

    return False


@router.message(F.chat.type == "private", F.text)
async def any_private(message: Message, config: Config, scheduler):
    user_id = message.from_user.id if message.from_user else 0
    raw = (message.text or "").strip()
    if not raw:
        return

    if user_id:
        await _remember(user_id, "user", raw)

    if await _try_local_parse(message, scheduler, config, raw):
        return

    if not config.openrouter_api_key:
        await message.answer("⛔ Не задан OPENROUTER_API_KEY в .env", reply_markup=main_keyboard())
        return

    try:
        ctx = await _ctx(message, config)
        ctx_messages = [{"role": h.get("role", "user"), "content": h.get("text", "")} for h in (ctx.get("dm_history") or [])]
        route = await route_message(
            config.openrouter_api_key,
            config.openrouter_model,
            raw,
            base_url=config.openrouter_base_url,
            ctx_messages=ctx_messages,
        )
    except Exception as e:
        log.exception("route_message failed: %s", e)
        await message.answer(f"Ошибка ИИ: {e}", reply_markup=main_keyboard())
        return

    if route.action == "chat":
        await message.answer(route.reply or "Не понял запрос.", reply_markup=main_keyboard())
        return

    fake = raw
    if route.action == "help":
        fake = "команды"
    elif route.action == "status":
        fake = "статус"
    elif route.action == "stats":
        fake = "статистика"
    elif route.action == "set_channel":
        fake = f"канал {route.args.get('channel', '')}"
    elif route.action == "set_topic":
        fake = f"тема: {route.args.get('topic', '')}"
    elif route.action == "schedule_add":
        fake = f"добавь расписание {route.args.get('time', '')} {route.args.get('days', '')}"
    elif route.action == "plan_add":
        dt = route.args.get("dt", "")
        topic = route.args.get("topic", "")
        prompt = route.args.get("prompt", "")
        fake = f"добавь в план {dt} тема: {topic}" if topic else f"добавь в план {dt} промпт: {prompt}"
    elif route.action in ("post_now", "post_prompt", "post_with_image"):
        fake = f"пост {route.args.get('text') or route.args.get('prompt') or route.args.get('topic') or raw}"
    elif route.action == "posts_on":
        await set_posts_enabled(True, owner_id=user_id)
        await message.answer("✅ Публикации включены.", reply_markup=main_keyboard())
        return
    elif route.action == "posts_off":
        await set_posts_enabled(False, owner_id=user_id)
        await message.answer("⛔ Публикации выключены.", reply_markup=main_keyboard())
        return
    else:
        await message.answer(route.reply or "Не понял запрос.", reply_markup=main_keyboard())
        return

    await _try_local_parse(message, scheduler, config, fake)