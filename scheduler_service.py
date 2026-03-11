
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

from aiogram import Bot

from db import (
    list_schedule,
    list_plan_items_active_not_posted,
    get_setting,
    get_posts_enabled,
    mark_plan_posted,
    log_post,
    list_owner_ids,
    log_news,
    set_setting,
    get_draft,
)
from content import generate_post_text
from image_search import find_image
from news_service import fetch_latest_news, build_news_post
from actions import publish_draft

MOSCOW_TZ = "Europe/Moscow"

DAY_MAP = {"mon": "mon", "tue": "tue", "wed": "wed", "thu": "thu", "fri": "fri", "sat": "sat", "sun": "sun"}

def _cron_days(days: str) -> str:
    days = (days or "*").strip().lower()
    if days == "*" or not days:
        return "mon,tue,wed,thu,fri,sat,sun"
    parts = [p.strip() for p in days.split(",") if p.strip()]
    ok = [DAY_MAP[p] for p in parts if p in DAY_MAP]
    return ",".join(ok) if ok else "mon,tue,wed,thu,fri,sat,sun"

def _parse_plan_dt(dt_str: str) -> datetime:
    s = dt_str.strip()
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s)
        else:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=ZoneInfo(MOSCOW_TZ))

class SchedulerService:
    def __init__(self, bot: Bot, tz: str):
        self.bot = bot
        self.tz = MOSCOW_TZ
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(MOSCOW_TZ))

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
        self.scheduler.add_job(self._job_news_tick, "interval", minutes=30, id="news_tick", replace_existing=True)

    async def rebuild_jobs(self):
        self.scheduler.remove_all_jobs()
        self.scheduler.add_job(self._job_news_tick, "interval", minutes=30, id="news_tick", replace_existing=True)

        schedules = await list_schedule(owner_id=None)
        for s in schedules:
            owner_id = int(s.get("owner_id") or 0)
            posting_mode = (await get_setting("posting_mode", owner_id=owner_id) or "both").strip().lower()
            if posting_mode not in ("both", "schedule"):
                continue
            if not int(s.get("enabled", 1)):
                continue
            hh, mm = str(s["time"]).split(":")
            trigger = CronTrigger(day_of_week=_cron_days(s["days"]), hour=int(hh), minute=int(mm), timezone=ZoneInfo(MOSCOW_TZ))
            self.scheduler.add_job(
                self._job_post_regular,
                trigger=trigger,
                id=f"schedule_{owner_id}_{s['id']}",
                replace_existing=True,
                misfire_grace_time=120,
                kwargs={"owner_id": owner_id},
            )

        items = await list_plan_items_active_not_posted(owner_id=None)
        for it in items:
            owner_id = int(it.get("owner_id") or 0)
            posting_mode = (await get_setting("posting_mode", owner_id=owner_id) or "both").strip().lower()
            if posting_mode not in ("both", "plan"):
                continue
            trigger = DateTrigger(run_date=_parse_plan_dt(it["dt"]))
            self.scheduler.add_job(
                self._job_post_plan_item,
                trigger=trigger,
                id=f"plan_{owner_id}_{it['id']}",
                replace_existing=True,
                misfire_grace_time=120,
                kwargs={
                    "item_id": it["id"],
                    "owner_id": owner_id,
                    "kind": it.get("kind", ""),
                    "payload": it.get("payload", ""),
                    "prompt": it.get("prompt", ""),
                    "topic_override": it.get("topic", ""),
                },
            )

    async def _job_post_regular(self, owner_id: int = 0):
        if not await get_posts_enabled(owner_id=owner_id):
            return
        channel = await get_setting("channel_target", owner_id=owner_id)
        if not channel:
            return
        api_key = (await get_setting("openrouter_api_key", owner_id=owner_id)) or getattr(getattr(self.bot, "_config", None), "openrouter_api_key", "")
        model = (await get_setting("openrouter_model", owner_id=owner_id)) or getattr(getattr(self.bot, "_config", None), "openrouter_model", "gpt-4o-mini")
        base_url = getattr(getattr(self.bot, "_config", None), "openrouter_base_url", None)
        topic = (await get_setting("topic", owner_id=owner_id)) or "массаж, упражнения, восстановление, осанка"
        if not api_key:
            return

        text = await generate_post_text(api_key, model, topic=topic, base_url=base_url)
        image_ref = await find_image(topic) or ""

        if image_ref:
            msg = await self.bot.send_photo(chat_id=channel, photo=image_ref, caption=text)
            content_type = "photo"
        else:
            msg = await self.bot.send_message(chat_id=channel, text=text)
            content_type = "text"

        await log_post(owner_id=owner_id, channel_target=channel, content_type=content_type, text=text, topic=topic, file_id=image_ref, telegram_message_id=getattr(msg, "message_id", 0))

    async def _job_post_plan_item(self, item_id: int, owner_id: int = 0, kind: str = "", payload: str = "", prompt: str = "", topic_override: str = ""):
        if not await get_posts_enabled(owner_id=owner_id):
            return
        channel = await get_setting("channel_target", owner_id=owner_id)
        if not channel:
            return

        if kind == "draft":
            try:
                draft_id = int(payload)
                draft = await get_draft(draft_id, owner_id=owner_id)
                if draft:
                    await publish_draft(self.bot, draft, owner_id=owner_id)
            finally:
                await mark_plan_posted(item_id, owner_id=owner_id)
            return

        api_key = (await get_setting("openrouter_api_key", owner_id=owner_id)) or getattr(getattr(self.bot, "_config", None), "openrouter_api_key", "")
        model = (await get_setting("openrouter_model", owner_id=owner_id)) or getattr(getattr(self.bot, "_config", None), "openrouter_model", "gpt-4o-mini")
        base_url = getattr(getattr(self.bot, "_config", None), "openrouter_base_url", None)
        topic = (topic_override or (await get_setting("topic", owner_id=owner_id)) or "").strip() or "массаж, упражнения, восстановление, осанка"
        if not api_key:
            return

        text = await generate_post_text(api_key, model, topic=topic, prompt=(prompt or payload or ""), base_url=base_url)
        image_ref = await find_image((prompt or payload or topic).strip() or topic) or ""

        if image_ref:
            msg = await self.bot.send_photo(chat_id=channel, photo=image_ref, caption=text)
            content_type = "photo"
        else:
            msg = await self.bot.send_message(chat_id=channel, text=text)
            content_type = "text"

        await log_post(owner_id=owner_id, channel_target=channel, content_type=content_type, text=text, prompt=prompt or payload, topic=topic, file_id=image_ref, telegram_message_id=getattr(msg, "message_id", 0))
        await mark_plan_posted(item_id, owner_id=owner_id)

    async def _job_news_tick(self):
        owner_ids = await list_owner_ids()
        cfg = getattr(self.bot, "_config", None)
        for owner_id in owner_ids:
            enabled = (await get_setting("news_enabled", owner_id=owner_id) or "0").strip() not in ("0", "false", "False")
            if not enabled:
                continue
            channel = await get_setting("channel_target", owner_id=owner_id)
            if not channel:
                continue
            interval_h = int((await get_setting("news_interval_hours", owner_id=owner_id) or "6").strip() or "6")
            last_ts = (await get_setting("news_last_posted_at", owner_id=owner_id) or "").strip()
            if last_ts:
                try:
                    last_dt = datetime.fromisoformat(last_ts)
                    if datetime.now(ZoneInfo(MOSCOW_TZ)) - last_dt.replace(tzinfo=ZoneInfo(MOSCOW_TZ)) < timedelta(hours=interval_h):
                        continue
                except Exception:
                    pass
            item = await fetch_latest_news(owner_id=owner_id)
            if not item or not cfg or not getattr(cfg, "openrouter_api_key", ""):
                continue
            text = await build_news_post(cfg, item, owner_id=owner_id)
            image_ref = await find_image(item.get("topic") or item.get("title") or "") or ""
            if image_ref:
                msg = await self.bot.send_photo(chat_id=channel, photo=image_ref, caption=text)
                content_type = "photo"
            else:
                msg = await self.bot.send_message(chat_id=channel, text=text)
                content_type = "text"
            await log_post(owner_id=owner_id, channel_target=channel, content_type=content_type, text=text, prompt=item.get("title", ""), topic=item.get("topic", ""), file_id=image_ref, telegram_message_id=getattr(msg, "message_id", 0))
            await log_news(item["link"], item.get("title", ""), owner_id=owner_id)
            await set_setting("news_last_posted_at", datetime.now(ZoneInfo(MOSCOW_TZ)).isoformat(timespec="seconds"), owner_id=owner_id)
