
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import db
import actions
from config import load_config
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="NeuroSMM Mini App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- helpers ----------

WEEKDAY_MAP = {
    0: "пн",
    1: "вт",
    2: "ср",
    3: "чт",
    4: "пт",
    5: "сб",
    6: "вс",
}


def _clean_text(v: str | None) -> str:
    return (v or "").strip()


async def _resolve_owner_id(owner_id: int | None = None) -> int:
    if owner_id not in (None, 0):
        return int(owner_id)
    try:
        ids = await db.list_owner_ids()
        if ids:
            return int(ids[0])
    except Exception:
        pass
    return 0


async def _owner_summary(owner_id: int) -> dict[str, Any]:
    channels = await db.list_channel_profiles(owner_id=owner_id)
    active = await db.get_active_channel_profile(owner_id=owner_id)
    drafts = await db.list_drafts(owner_id=owner_id, limit=50)
    plan = await db.list_plan_items(owner_id=owner_id, limit=300)
    schedules = await db.list_schedules(owner_id=owner_id)
    stats = await db.get_post_stats(owner_id=owner_id)

    posts_enabled = await db.get_setting("posts_enabled", owner_id=owner_id) or "1"
    posting_mode = await db.get_setting("posting_mode", owner_id=owner_id) or "both"
    news_enabled = await db.get_setting("news_enabled", owner_id=owner_id) or "0"
    news_interval_hours = await db.get_setting("news_interval_hours", owner_id=owner_id) or "6"
    news_sources = await db.get_setting("news_sources", owner_id=owner_id) or ""
    topic = await db.get_setting("topic", owner_id=owner_id) or (active.get("topic", "") if active else "")
    channel_target = await db.get_setting("channel_target", owner_id=owner_id) or (active.get("channel_target", "") if active else "")

    return {
        "owner_id": owner_id,
        "channels": channels,
        "active_channel": active,
        "drafts": drafts,
        "plan": plan,
        "schedules": schedules,
        "stats": stats,
        "settings": {
            "posts_enabled": str(posts_enabled),
            "posting_mode": str(posting_mode),
            "news_enabled": str(news_enabled),
            "news_interval_hours": str(news_interval_hours),
            "news_sources": str(news_sources),
            "topic": str(topic),
            "channel_target": str(channel_target),
        },
    }


def _split_sources(raw: str) -> list[str]:
    parts = re.split(r"[\n,; ]+", raw or "")
    return [p.strip() for p in parts if p.strip()]


def _days_label(days: str) -> str:
    value = (days or "*").strip()
    if value == "*":
        return "Каждый день"
    return ", ".join(p.strip() for p in value.split(",") if p.strip())


def _idea_buckets(topic: str) -> list[str]:
    core = topic.strip() or "теме канала"
    return [
        f"Быстрый разбор главной новости по {core}",
        f"Практический совет по {core}",
        f"Топ-5 ошибок новичков в {core}",
        f"Краткий гайд: с чего начать в {core}",
        f"Разбор тренда недели в {core}",
        f"Миф или правда: популярное заблуждение о {core}",
        f"Инструменты и сервисы для работы с {core}",
        f"Мини-кейс: реальный сценарий в {core}",
        f"Чек-лист для подписчиков по {core}",
        f"Подборка полезных ресурсов по {core}",
        f"Что изменилось в нише {core} за последнее время",
        f"Сравнение подходов и стратегий в {core}",
        f"Вопрос-ответ подписчиков по {core}",
        f"Прогноз и личное мнение по развитию {core}",
    ]


def _generate_plan_items(start_date: str | None, days: int, posts_per_day: int, topic: str, post_time: str) -> list[dict[str, str]]:
    try:
        dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else datetime.now().date()
    except Exception:
        dt = datetime.now().date()
    if days < 1:
        days = 1
    if days > 90:
        days = 90
    if posts_per_day < 1:
        posts_per_day = 1
    if posts_per_day > 4:
        posts_per_day = 4
    base_hour, base_minute = 12, 0
    try:
        hh, mm = (post_time or "12:00").split(":")
        base_hour, base_minute = int(hh), int(mm)
    except Exception:
        pass

    bucket = _idea_buckets(topic)
    out = []
    idx = 0
    for day_i in range(days):
        cur = dt + timedelta(days=day_i)
        for slot in range(posts_per_day):
            total_minutes = base_hour * 60 + base_minute + slot * 180
            hh = (total_minutes // 60) % 24
            mm = total_minutes % 60
            prompt = bucket[idx % len(bucket)]
            idx += 1
            out.append(
                {
                    "dt": f"{cur.isoformat()} {hh:02d}:{mm:02d}",
                    "prompt": prompt,
                    "kind": "prompt",
                }
            )
    return out


async def _create_bot() -> Bot:
    config = load_config()
    return Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=None))


# ---------- models ----------

class OwnerPayload(BaseModel):
    owner_id: int | None = None

class ChannelCreate(BaseModel):
    owner_id: int | None = None
    title: str = ""
    channel_target: str
    topic: str = ""
    make_active: bool = True

class ChannelActivate(BaseModel):
    owner_id: int | None = None
    profile_id: int

class DraftCreate(BaseModel):
    owner_id: int | None = None
    text: str = ""
    prompt: str = ""
    topic: str = ""
    channel_target: str = ""
    media_type: str = "none"
    media_ref: str = ""
    buttons_json: str = "[]"
    pin_post: int = 0
    comments_enabled: int = 1
    ad_mark: int = 0
    first_reaction: str = ""
    reply_to_message_id: int = 0

class DraftUpdate(BaseModel):
    owner_id: int | None = None
    text: str | None = None
    prompt: str | None = None
    topic: str | None = None
    channel_target: str | None = None
    media_type: str | None = None
    media_ref: str | None = None
    buttons_json: str | None = None
    pin_post: int | None = None
    comments_enabled: int | None = None
    ad_mark: int | None = None
    first_reaction: str | None = None
    reply_to_message_id: int | None = None
    status: str | None = None

class DraftPublish(BaseModel):
    owner_id: int | None = None
    draft_id: int

class DraftGenerate(BaseModel):
    owner_id: int | None = None
    prompt: str

class PlanGenerate(BaseModel):
    owner_id: int | None = None
    start_date: str | None = None
    days: int = Field(default=30, ge=1, le=90)
    posts_per_day: int = Field(default=1, ge=1, le=4)
    topic: str = ""
    post_time: str = "12:00"
    clear_existing: bool = True

class PlanCreate(BaseModel):
    owner_id: int | None = None
    dt: str
    topic: str = ""
    prompt: str = ""

class PlanUpdate(BaseModel):
    owner_id: int | None = None
    dt: str | None = None
    topic: str | None = None
    prompt: str | None = None

class ScheduleCreate(BaseModel):
    owner_id: int | None = None
    time_hhmm: str
    days: str = "*"

class SettingsUpdate(BaseModel):
    owner_id: int | None = None
    posts_enabled: str | None = None
    posting_mode: str | None = None
    news_enabled: str | None = None
    news_interval_hours: str | None = None
    news_sources: str | None = None
    topic: str | None = None

# ---------- startup ----------

@app.on_event("startup")
async def startup():
    await db.init_db()

# ---------- api ----------

@app.get("/api/bootstrap")
async def bootstrap(owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    owners = await db.list_owner_ids()
    payload = await _owner_summary(resolved)
    payload["owners"] = owners
    payload["meta"] = {
        "days_options": [7, 14, 30, 60],
        "posting_modes": ["both", "news", "posts"],
    }
    return payload


@app.get("/api/owners")
async def owners():
    ids = await db.list_owner_ids()
    return {"owners": ids, "default_owner_id": ids[0] if ids else 0}


@app.post("/api/channels")
async def create_channel(data: ChannelCreate):
    owner_id = await _resolve_owner_id(data.owner_id)
    title = _clean_text(data.title) or _clean_text(data.channel_target)
    await db.upsert_channel_profile(
        owner_id=owner_id,
        channel_target=_clean_text(data.channel_target),
        title=title,
        topic=_clean_text(data.topic),
        make_active=bool(data.make_active),
    )
    if data.make_active:
        await db.set_setting("channel_target", _clean_text(data.channel_target), owner_id=owner_id)
        await db.set_setting("topic", _clean_text(data.topic), owner_id=owner_id)
    return await _owner_summary(owner_id)


@app.post("/api/channels/activate")
async def activate_channel(data: ChannelActivate):
    owner_id = await _resolve_owner_id(data.owner_id)
    profile = await db.set_active_channel_profile(data.profile_id, owner_id=owner_id)
    if not profile:
        raise HTTPException(404, "Канал не найден")
    return await _owner_summary(owner_id)


@app.get("/api/drafts")
async def list_drafts(owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    return await db.list_drafts(owner_id=resolved, limit=100)


@app.post("/api/drafts")
async def create_draft(data: DraftCreate):
    owner_id = await _resolve_owner_id(data.owner_id)
    channel_target = _clean_text(data.channel_target) or (await db.get_setting("channel_target", owner_id=owner_id) or "")
    topic = _clean_text(data.topic) or (await db.get_setting("topic", owner_id=owner_id) or "")
    draft_id = await db.create_draft(
        owner_id=owner_id,
        channel_target=channel_target,
        text=data.text,
        prompt=data.prompt,
        topic=topic,
        media_type=data.media_type,
        media_ref=data.media_ref,
        buttons_json=data.buttons_json,
        pin_post=int(data.pin_post),
        comments_enabled=int(data.comments_enabled),
        ad_mark=int(data.ad_mark),
        first_reaction=data.first_reaction,
        reply_to_message_id=int(data.reply_to_message_id or 0),
        status="draft",
    )
    return {"ok": True, "draft": await db.get_draft(draft_id, owner_id=owner_id)}

@app.patch("/api/drafts/{draft_id}")
async def patch_draft(draft_id: int, data: DraftUpdate):
    owner_id = await _resolve_owner_id(data.owner_id)
    fields = data.model_dump(exclude_unset=True)
    fields.pop("owner_id", None)
    for key, value in fields.items():
        await db.update_draft_field(draft_id, owner_id, key, value)
    draft = await db.get_draft(draft_id, owner_id=owner_id)
    if not draft:
        raise HTTPException(404, "Черновик не найден")
    return {"ok": True, "draft": draft}

@app.delete("/api/drafts/{draft_id}")
async def remove_draft(draft_id: int, owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    await db.delete_draft(draft_id, owner_id=resolved)
    return {"ok": True}

@app.post("/api/drafts/generate")
async def generate_draft(data: DraftGenerate):
    owner_id = await _resolve_owner_id(data.owner_id)
    config = load_config()
    draft_id = await actions.create_generated_draft(config, data.prompt, owner_id=owner_id, force_image=True)
    return {"ok": True, "draft": await db.get_draft(draft_id, owner_id=owner_id)}

@app.post("/api/drafts/publish")
async def publish_draft(data: DraftPublish):
    owner_id = await _resolve_owner_id(data.owner_id)
    draft = await db.get_draft(data.draft_id, owner_id=owner_id)
    if not draft:
        raise HTTPException(404, "Черновик не найден")
    bot = await _create_bot()
    try:
        result = await actions.publish_draft(bot, draft, owner_id=owner_id)
    finally:
        await bot.session.close()
    if not result.ok:
        raise HTTPException(400, result.error or "Ошибка публикации")
    return {"ok": True, "message": "Пост опубликован"}

@app.get("/api/plan")
async def list_plan(owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    return await db.list_plan_items(owner_id=resolved, limit=500)

@app.post("/api/plan")
async def create_plan_item(data: PlanCreate):
    owner_id = await _resolve_owner_id(data.owner_id)
    await db.add_plan_item(
        dt=_clean_text(data.dt),
        owner_id=owner_id,
        topic=_clean_text(data.topic),
        prompt=_clean_text(data.prompt),
    )
    return {"ok": True}

@app.patch("/api/plan/{item_id}")
async def patch_plan_item(item_id: int, data: PlanUpdate):
    owner_id = await _resolve_owner_id(data.owner_id)
    await db.update_plan_item(
        item_id,
        owner_id=owner_id,
        dt=data.dt,
        topic=data.topic,
        prompt=data.prompt,
    )
    item = await db.get_plan_item(item_id, owner_id=owner_id)
    if not item:
        raise HTTPException(404, "Элемент плана не найден")
    return {"ok": True, "item": item}

@app.delete("/api/plan/{item_id}")
async def delete_plan_item(item_id: int, owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    await db.delete_plan_item(item_id, owner_id=resolved)
    return {"ok": True}

@app.post("/api/plan/generate")
async def generate_plan(data: PlanGenerate):
    owner_id = await _resolve_owner_id(data.owner_id)
    active = await db.get_active_channel_profile(owner_id=owner_id)
    topic = _clean_text(data.topic) or (active.get("topic", "") if active else "") or (await db.get_setting("topic", owner_id=owner_id) or "")
    items = _generate_plan_items(data.start_date, data.days, data.posts_per_day, topic, data.post_time)
    if data.clear_existing:
        await db.clear_unposted_plan_items(owner_id=owner_id)
    for item in items:
        await db.add_plan_item(
            dt=item["dt"],
            owner_id=owner_id,
            prompt=item["prompt"],
        )
    return {"ok": True, "created": len(items)}

@app.get("/api/schedules")
async def list_schedules(owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    rows = await db.list_schedules(owner_id=resolved)
    for row in rows:
        row["days_label"] = _days_label(row.get("days", "*"))
    return rows

@app.post("/api/schedules")
async def create_schedule(data: ScheduleCreate):
    owner_id = await _resolve_owner_id(data.owner_id)
    await db.add_schedule(time_hhmm=_clean_text(data.time_hhmm), days=_clean_text(data.days) or "*", owner_id=owner_id)
    return {"ok": True}

@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int, owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    rows = await db.list_schedules(owner_id=resolved)
    target = next((r for r in rows if int(r["id"]) == int(schedule_id)), None)
    if not target:
        raise HTTPException(404, "Расписание не найдено")
    # db has no delete one, so rewrite
    await db.clear_schedules(owner_id=resolved)
    for row in rows:
        if int(row["id"]) != int(schedule_id):
            await db.add_schedule(row["time_hhmm"], row["days"], owner_id=resolved)
    return {"ok": True}

@app.get("/api/settings")
async def settings(owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    return (await _owner_summary(resolved))["settings"]

@app.patch("/api/settings")
async def patch_settings(data: SettingsUpdate):
    owner_id = await _resolve_owner_id(data.owner_id)
    fields = data.model_dump(exclude_unset=True)
    fields.pop("owner_id", None)
    for key, value in fields.items():
        await db.set_setting(key, str(value), owner_id=owner_id)
    if "topic" in fields:
        active = await db.get_active_channel_profile(owner_id=owner_id)
        if active:
            await db.sync_channel_profile_topic(owner_id, active.get("channel_target", ""), str(fields["topic"]))
    return {"ok": True, "settings": (await _owner_summary(owner_id))["settings"]}

@app.get("/api/stats")
async def stats(owner_id: int | None = None):
    resolved = await _resolve_owner_id(owner_id)
    return await db.get_post_stats(owner_id=resolved)

app.mount("/", StaticFiles(directory=str(BASE_DIR / "miniapp"), html=True), name="miniapp")
