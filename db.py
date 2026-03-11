
from __future__ import annotations

import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "bot.db"


def _scope_key(key: str, owner_id: int | None = None) -> str:
    if owner_id in (None, 0):
        return key
    return f"u:{int(owner_id)}:{key}"


async def _column_exists(db: aiosqlite.Connection, table: str, column: str) -> bool:
    cur = await db.execute(f"PRAGMA table_info({table})")
    rows = await cur.fetchall()
    return any(r[1] == column for r in rows)


async def _ensure_settings_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


async def _ensure_schedules_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_hhmm TEXT NOT NULL,
            days TEXT NOT NULL DEFAULT '*'
        )
        """
    )
    if not await _column_exists(db, "schedules", "enabled"):
        await db.execute("ALTER TABLE schedules ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
    if not await _column_exists(db, "schedules", "owner_id"):
        await db.execute("ALTER TABLE schedules ADD COLUMN owner_id INTEGER NOT NULL DEFAULT 0")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_schedules_owner ON schedules(owner_id, id)")


async def _ensure_plan_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    if not await _column_exists(db, "plan_items", "enabled"):
        await db.execute("ALTER TABLE plan_items ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
    if not await _column_exists(db, "plan_items", "posted"):
        await db.execute("ALTER TABLE plan_items ADD COLUMN posted INTEGER NOT NULL DEFAULT 0")
    if not await _column_exists(db, "plan_items", "owner_id"):
        await db.execute("ALTER TABLE plan_items ADD COLUMN owner_id INTEGER NOT NULL DEFAULT 0")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_plan_items_owner ON plan_items(owner_id, id)")


async def _ensure_dm_memory_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS dm_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            ts TEXT NOT NULL
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_dm_memory_user ON dm_memory(user_id, id DESC)")


async def _ensure_post_log_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS post_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL DEFAULT 0,
            channel_target TEXT NOT NULL DEFAULT '',
            content_type TEXT NOT NULL DEFAULT 'text',
            text TEXT NOT NULL DEFAULT '',
            prompt TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            file_id TEXT NOT NULL DEFAULT '',
            telegram_message_id INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_post_logs_owner ON post_logs(owner_id, id DESC)")


async def _ensure_draft_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS draft_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL DEFAULT 0,
            channel_target TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL DEFAULT '',
            prompt TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            media_type TEXT NOT NULL DEFAULT 'none',
            media_ref TEXT NOT NULL DEFAULT '',
            buttons_json TEXT NOT NULL DEFAULT '[]',
            pin_post INTEGER NOT NULL DEFAULT 0,
            comments_enabled INTEGER NOT NULL DEFAULT 1,
            ad_mark INTEGER NOT NULL DEFAULT 0,
            first_reaction TEXT NOT NULL DEFAULT '',
            reply_to_message_id INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_draft_posts_owner ON draft_posts(owner_id, id DESC)")


async def _ensure_channel_profiles_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL DEFAULT '',
            channel_target TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_profiles_unique ON channel_profiles(owner_id, channel_target)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_channel_profiles_owner ON channel_profiles(owner_id, is_active, id)")


async def _ensure_news_schema(db: aiosqlite.Connection):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS news_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL DEFAULT 0,
            source_url TEXT NOT NULL DEFAULT '',
            source_title TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_news_logs_owner ON news_logs(owner_id, id DESC)")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_settings_schema(db)
        await _ensure_schedules_schema(db)
        await _ensure_plan_schema(db)
        await _ensure_dm_memory_schema(db)
        await _ensure_post_log_schema(db)
        await _ensure_draft_schema(db)
        await _ensure_news_schema(db)
        await _ensure_channel_profiles_schema(db)

        defaults = {
            "posts_enabled": "1",
            "posting_mode": "both",
            "news_enabled": "0",
            "news_interval_hours": "6",
            "news_sources": "who.int,mayoclinic.org,nih.gov",
        }
        for k, v in defaults.items():
            cur = await db.execute("SELECT value FROM settings WHERE key=?", (k,))
            row = await cur.fetchone()
            if not row:
                await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, v))
        await db.commit()


# ---------- settings ----------
async def get_setting(key: str, owner_id: int | None = None) -> str | None:
    scoped = _scope_key(key, owner_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (scoped,))
        row = await cur.fetchone()
        if row:
            return row[0]
        if owner_id not in (None, 0):
            cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = await cur.fetchone()
            return row[0] if row else None
        return None


async def set_setting(key: str, value: str, owner_id: int | None = None):
    scoped = _scope_key(key, owner_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (scoped, value))
        await db.commit()


async def get_posts_enabled(owner_id: int | None = None) -> bool:
    v = await get_setting("posts_enabled", owner_id=owner_id)
    return (v or "1").strip() not in ("0", "false", "False", "no", "No")


async def set_posts_enabled(enabled: bool, owner_id: int | None = None):
    await set_setting("posts_enabled", "1" if enabled else "0", owner_id=owner_id)


# ---------- schedules ----------
async def list_schedules(owner_id: int | None = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        if owner_id is None:
            cur = await db.execute(
                "SELECT id, time_hhmm, days, enabled, owner_id FROM schedules ORDER BY owner_id ASC, id ASC"
            )
            rows = await cur.fetchall()
        else:
            cur = await db.execute(
                "SELECT id, time_hhmm, days, enabled, owner_id FROM schedules WHERE owner_id=? ORDER BY id ASC",
                (int(owner_id),),
            )
            rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "time_hhmm": r[1],
                "time": r[1],
                "days": r[2],
                "enabled": int(r[3]),
                "owner_id": int(r[4]),
            }
            for r in rows
        ]


async def list_schedule(owner_id: int | None = 0):
    return await list_schedules(owner_id=owner_id)


async def add_schedule(time_hhmm: str, days: str = "*", owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO schedules(time_hhmm, days, enabled, owner_id) VALUES(?,?,1,?)",
            (time_hhmm.strip(), (days or "*").strip(), int(owner_id or 0)),
        )
        await db.commit()


async def clear_schedules(owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        if owner_id is None:
            await db.execute("DELETE FROM schedules")
        else:
            await db.execute("DELETE FROM schedules WHERE owner_id=?", (int(owner_id),))
        await db.commit()


# ---------- plan ----------
async def add_plan_item(
    dt: str,
    kind: str | None = None,
    payload: str | None = None,
    enabled: bool = True,
    *,
    topic: str = "",
    prompt: str = "",
    posted: int = 0,
    owner_id: int | None = 0,
):
    dt = (dt or "").strip()
    if kind and payload is not None and not topic and not prompt:
        _kind = kind.strip()
        _payload = payload.strip()
    else:
        topic = (topic or "").strip()
        prompt = (prompt or "").strip()
        if prompt:
            _kind = "prompt"
            _payload = prompt
        else:
            _kind = "topic"
            _payload = topic
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO plan_items(dt, kind, payload, created_at, enabled, posted, owner_id)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                dt, _kind, _payload, datetime.utcnow().isoformat(timespec="seconds"),
                1 if enabled else 0, int(posted), int(owner_id or 0),
            ),
        )
        await db.commit()


async def list_plan_items(limit: int = 50, owner_id: int | None = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        if owner_id is None:
            cur = await db.execute(
                "SELECT id, dt, kind, payload, created_at, enabled, posted, owner_id FROM plan_items ORDER BY dt ASC, id ASC LIMIT ?",
                (int(limit),),
            )
        else:
            cur = await db.execute(
                "SELECT id, dt, kind, payload, created_at, enabled, posted, owner_id FROM plan_items WHERE owner_id=? ORDER BY dt ASC, id ASC LIMIT ?",
                (int(owner_id), int(limit)),
            )
        rows = await cur.fetchall()
        out = []
        for r in rows:
            topic = r[3] if r[2] == "topic" else ""
            prompt = r[3] if r[2] == "prompt" else ""
            out.append(
                {
                    "id": r[0],
                    "dt": r[1],
                    "kind": r[2],
                    "payload": r[3],
                    "created_at": r[4],
                    "enabled": int(r[5]),
                    "posted": int(r[6]),
                    "owner_id": int(r[7]),
                    "topic": topic,
                    "prompt": prompt,
                }
            )
        return out


async def list_plan_items_active_not_posted(owner_id: int | None = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        if owner_id is None:
            cur = await db.execute(
                "SELECT id, dt, kind, payload, created_at, enabled, posted, owner_id FROM plan_items WHERE enabled=1 AND posted=0 ORDER BY dt ASC, id ASC"
            )
        else:
            cur = await db.execute(
                "SELECT id, dt, kind, payload, created_at, enabled, posted, owner_id FROM plan_items WHERE enabled=1 AND posted=0 AND owner_id=? ORDER BY dt ASC, id ASC",
                (int(owner_id),),
            )
        rows = await cur.fetchall()
        out = []
        for r in rows:
            topic = r[3] if r[2] == "topic" else ""
            prompt = r[3] if r[2] == "prompt" else ""
            out.append(
                {
                    "id": r[0],
                    "dt": r[1],
                    "kind": r[2],
                    "payload": r[3],
                    "created_at": r[4],
                    "enabled": int(r[5]),
                    "posted": int(r[6]),
                    "owner_id": int(r[7]),
                    "topic": topic,
                    "prompt": prompt,
                }
            )
        return out


async def mark_plan_posted(item_id: int, owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE plan_items SET posted=1 WHERE id=? AND owner_id=?", (int(item_id), int(owner_id or 0)))
        await db.commit()


async def delete_plan_item(item_id: int, owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM plan_items WHERE id=? AND owner_id=?", (int(item_id), int(owner_id or 0)))
        await db.commit()


async def get_plan_item(item_id: int, owner_id: int | None = 0) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, dt, kind, payload, created_at, enabled, posted, owner_id FROM plan_items WHERE id=? AND owner_id=? LIMIT 1",
            (int(item_id), int(owner_id or 0)),
        )
        r = await cur.fetchone()
        if not r:
            return None
        topic = r[3] if r[2] == "topic" else ""
        prompt = r[3] if r[2] == "prompt" else ""
        return {
            "id": r[0],
            "dt": r[1],
            "kind": r[2],
            "payload": r[3],
            "created_at": r[4],
            "enabled": int(r[5]),
            "posted": int(r[6]),
            "owner_id": int(r[7]),
            "topic": topic,
            "prompt": prompt,
        }


async def update_plan_item(item_id: int, owner_id: int | None = 0, *, dt: str | None = None, topic: str | None = None, prompt: str | None = None):
    fields = []
    values = []
    if dt is not None:
        fields.append("dt=?")
        values.append((dt or "").strip())
    if topic is not None:
        fields.append("kind=?")
        fields.append("payload=?")
        values.extend(["topic", (topic or "").strip()])
    elif prompt is not None:
        fields.append("kind=?")
        fields.append("payload=?")
        values.extend(["prompt", (prompt or "").strip()])
    if not fields:
        return
    values.extend([int(item_id), int(owner_id or 0)])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE plan_items SET {', '.join(fields)} WHERE id=? AND owner_id=?", tuple(values))
        await db.commit()


async def clear_unposted_plan_items(owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        if owner_id is None:
            await db.execute("DELETE FROM plan_items WHERE posted=0")
        else:
            await db.execute("DELETE FROM plan_items WHERE owner_id=? AND posted=0", (int(owner_id),))
        await db.commit()


# ---------- dm memory ----------
async def dm_add_message(user_id: int, role: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO dm_memory(user_id, role, text, ts) VALUES(?,?,?,?)",
            (int(user_id), role, text, datetime.utcnow().isoformat(timespec="seconds")),
        )
        await db.commit()


async def dm_get_recent(user_id: int, limit: int = 14) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT role, text, ts FROM dm_memory WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (int(user_id), int(limit)),
        )
        rows = await cur.fetchall()
        return [{"role": r[0], "text": r[1], "ts": r[2]} for r in reversed(rows)]


# ---------- post logs ----------
async def log_post(
    *,
    owner_id: int | None = 0,
    channel_target: str,
    content_type: str = "text",
    text: str = "",
    prompt: str = "",
    topic: str = "",
    file_id: str = "",
    telegram_message_id: int = 0,
    created_at: Optional[str] = None,
):
    created_at = created_at or datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO post_logs(owner_id, channel_target, content_type, text, prompt, topic, file_id, telegram_message_id, created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                int(owner_id or 0),
                channel_target,
                content_type,
                text,
                prompt,
                topic,
                file_id or "",
                int(telegram_message_id or 0),
                created_at,
            ),
        )
        await db.commit()


async def list_recent_posts(owner_id: int | None = 0, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        if owner_id is None:
            cur = await db.execute(
                "SELECT id, owner_id, channel_target, content_type, text, prompt, topic, file_id, telegram_message_id, created_at FROM post_logs ORDER BY id DESC LIMIT ?",
                (int(limit),),
            )
        else:
            cur = await db.execute(
                "SELECT id, owner_id, channel_target, content_type, text, prompt, topic, file_id, telegram_message_id, created_at FROM post_logs WHERE owner_id=? ORDER BY id DESC LIMIT ?",
                (int(owner_id), int(limit)),
            )
        rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "owner_id": int(r[1]),
                "channel_target": r[2],
                "content_type": r[3],
                "text": r[4],
                "prompt": r[5],
                "topic": r[6],
                "file_id": r[7],
                "telegram_message_id": int(r[8]),
                "created_at": r[9],
            }
            for r in rows
        ]


async def get_post_stats(owner_id: int | None = 0) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        where = ""
        params: tuple = ()
        if owner_id is not None:
            where = "WHERE owner_id=?"
            params = (int(owner_id),)

        cur = await db.execute(
            f"SELECT COUNT(*), COALESCE(SUM(CASE WHEN content_type='photo' THEN 1 ELSE 0 END), 0), COALESCE(AVG(LENGTH(text)), 0) FROM post_logs {where}",
            params,
        )
        total, photo_count, avg_len = await cur.fetchone()

        cur = await db.execute(
            f"SELECT COUNT(*) FROM schedules {'WHERE owner_id=?' if owner_id is not None else ''}",
            params,
        )
        schedules_total = (await cur.fetchone())[0]

        cur = await db.execute(
            f"SELECT COUNT(*), COALESCE(SUM(CASE WHEN posted=1 THEN 1 ELSE 0 END), 0) FROM plan_items {'WHERE owner_id=?' if owner_id is not None else ''}",
            params,
        )
        plan_total, plan_posted = await cur.fetchone()

        return {
            "total_posts": int(total or 0),
            "photo_posts": int(photo_count or 0),
            "text_posts": int((total or 0) - (photo_count or 0)),
            "avg_length": int(avg_len or 0),
            "schedules_total": int(schedules_total or 0),
            "plan_total": int(plan_total or 0),
            "plan_posted": int(plan_posted or 0),
        }


# ---------- draft editor ----------
async def create_draft(
    *,
    owner_id: int | None = 0,
    channel_target: str = "",
    text: str = "",
    prompt: str = "",
    topic: str = "",
    media_type: str = "none",
    media_ref: str = "",
    buttons_json: str = "[]",
    pin_post: int = 0,
    comments_enabled: int = 1,
    ad_mark: int = 0,
    first_reaction: str = "",
    reply_to_message_id: int = 0,
    status: str = "draft",
) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO draft_posts(
                owner_id, channel_target, text, prompt, topic, media_type, media_ref, buttons_json,
                pin_post, comments_enabled, ad_mark, first_reaction, reply_to_message_id, status, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(owner_id or 0),
                channel_target,
                text,
                prompt,
                topic,
                media_type,
                media_ref,
                buttons_json,
                int(pin_post),
                int(comments_enabled),
                int(ad_mark),
                first_reaction,
                int(reply_to_message_id or 0),
                status,
                now,
                now,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_draft(draft_id: int, owner_id: int | None = 0) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT id, owner_id, channel_target, text, prompt, topic, media_type, media_ref, buttons_json,
                   pin_post, comments_enabled, ad_mark, first_reaction, reply_to_message_id, status, created_at, updated_at
            FROM draft_posts WHERE id=? AND owner_id=?
            """,
            (int(draft_id), int(owner_id or 0)),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "owner_id": row[1],
            "channel_target": row[2],
            "text": row[3],
            "prompt": row[4],
            "topic": row[5],
            "media_type": row[6],
            "media_ref": row[7],
            "buttons_json": row[8],
            "pin_post": int(row[9]),
            "comments_enabled": int(row[10]),
            "ad_mark": int(row[11]),
            "first_reaction": row[12],
            "reply_to_message_id": int(row[13]),
            "status": row[14],
            "created_at": row[15],
            "updated_at": row[16],
        }


async def get_latest_draft(owner_id: int | None = 0) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT id, owner_id, channel_target, text, prompt, topic, media_type, media_ref, buttons_json,
                   pin_post, comments_enabled, ad_mark, first_reaction, reply_to_message_id, status, created_at, updated_at
            FROM draft_posts WHERE owner_id=? AND status='draft' ORDER BY id DESC LIMIT 1
            """,
            (int(owner_id or 0),),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "owner_id": row[1],
            "channel_target": row[2],
            "text": row[3],
            "prompt": row[4],
            "topic": row[5],
            "media_type": row[6],
            "media_ref": row[7],
            "buttons_json": row[8],
            "pin_post": int(row[9]),
            "comments_enabled": int(row[10]),
            "ad_mark": int(row[11]),
            "first_reaction": row[12],
            "reply_to_message_id": int(row[13]),
            "status": row[14],
            "created_at": row[15],
            "updated_at": row[16],
        }


async def update_draft_field(draft_id: int, owner_id: int | None, field: str, value):
    allowed = {
        "channel_target",
        "text",
        "prompt",
        "topic",
        "media_type",
        "media_ref",
        "buttons_json",
        "pin_post",
        "comments_enabled",
        "ad_mark",
        "first_reaction",
        "reply_to_message_id",
        "status",
    }
    if field not in allowed:
        raise ValueError("Unsupported draft field")
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE draft_posts SET {field}=?, updated_at=? WHERE id=? AND owner_id=?",
            (value, now, int(draft_id), int(owner_id or 0)),
        )
        await db.commit()


async def delete_draft(draft_id: int, owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM draft_posts WHERE id=? AND owner_id=?", (int(draft_id), int(owner_id or 0)))
        await db.commit()


async def list_drafts(owner_id: int | None = 0, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT id, owner_id, channel_target, text, prompt, topic, media_type, media_ref, buttons_json,
                   pin_post, comments_enabled, ad_mark, first_reaction, reply_to_message_id, status, created_at, updated_at
            FROM draft_posts WHERE owner_id=? ORDER BY id DESC LIMIT ?
            """,
            (int(owner_id or 0), int(limit)),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "owner_id": r[1],
                "channel_target": r[2],
                "text": r[3],
                "prompt": r[4],
                "topic": r[5],
                "media_type": r[6],
                "media_ref": r[7],
                "buttons_json": r[8],
                "pin_post": int(r[9]),
                "comments_enabled": int(r[10]),
                "ad_mark": int(r[11]),
                "first_reaction": r[12],
                "reply_to_message_id": int(r[13]),
                "status": r[14],
                "created_at": r[15],
                "updated_at": r[16],
            }
            for r in rows
        ]


# ---------- owner discovery ----------
async def list_owner_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        ids = set()
        for table in ("schedules", "plan_items", "post_logs", "draft_posts", "news_logs", "channel_profiles"):
            try:
                cur = await db.execute(f"SELECT DISTINCT owner_id FROM {table}")
                rows = await cur.fetchall()
                ids.update(int(r[0] or 0) for r in rows)
            except Exception:
                pass
        cur = await db.execute("SELECT key FROM settings WHERE key LIKE 'u:%:%'")
        for (key,) in await cur.fetchall():
            try:
                ids.add(int(str(key).split(":", 2)[1]))
            except Exception:
                pass
        ids.discard(0)
        return sorted(ids)


# ---------- news helpers ----------
async def is_news_used(source_url: str, owner_id: int | None = 0) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM news_logs WHERE owner_id=? AND source_url=? LIMIT 1",
            (int(owner_id or 0), source_url),
        )
        row = await cur.fetchone()
        return row is not None


async def log_news(source_url: str, source_title: str = "", owner_id: int | None = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO news_logs(owner_id, source_url, source_title, created_at) VALUES(?,?,?,?)",
            (int(owner_id or 0), source_url, source_title, datetime.utcnow().isoformat(timespec="seconds")),
        )
        await db.commit()


# ---------- channels ----------
async def upsert_channel_profile(
    owner_id: int | None,
    channel_target: str,
    *,
    title: str = "",
    topic: str = "",
    make_active: bool = True,
):
    owner = int(owner_id or 0)
    channel_target = (channel_target or "").strip()
    if not channel_target:
        return
    title = (title or channel_target).strip()
    topic = (topic or "").strip()
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        if make_active:
            await db.execute("UPDATE channel_profiles SET is_active=0 WHERE owner_id=?", (owner,))
        cur = await db.execute(
            "SELECT id, topic, title FROM channel_profiles WHERE owner_id=? AND channel_target=? LIMIT 1",
            (owner, channel_target),
        )
        row = await cur.fetchone()
        if row:
            new_title = title or row[2] or channel_target
            new_topic = topic or row[1] or ""
            await db.execute(
                "UPDATE channel_profiles SET title=?, topic=?, is_active=?, updated_at=? WHERE id=?",
                (new_title, new_topic, 1 if make_active else 0, now, int(row[0])),
            )
        else:
            await db.execute(
                "INSERT INTO channel_profiles(owner_id, title, channel_target, topic, is_active, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                (owner, title, channel_target, topic, 1 if make_active else 0, now, now),
            )
        await db.commit()


async def list_channel_profiles(owner_id: int | None = 0) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, owner_id, title, channel_target, topic, is_active, created_at, updated_at FROM channel_profiles WHERE owner_id=? ORDER BY is_active DESC, id ASC",
            (int(owner_id or 0),),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": int(r[0]),
                "owner_id": int(r[1]),
                "title": r[2],
                "channel_target": r[3],
                "topic": r[4],
                "is_active": int(r[5]),
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]


async def get_active_channel_profile(owner_id: int | None = 0) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, owner_id, title, channel_target, topic, is_active, created_at, updated_at FROM channel_profiles WHERE owner_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",
            (int(owner_id or 0),),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return {
            "id": int(r[0]),
            "owner_id": int(r[1]),
            "title": r[2],
            "channel_target": r[3],
            "topic": r[4],
            "is_active": int(r[5]),
            "created_at": r[6],
            "updated_at": r[7],
        }


async def set_active_channel_profile(profile_id: int, owner_id: int | None = 0) -> dict | None:
    owner = int(owner_id or 0)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE channel_profiles SET is_active=0 WHERE owner_id=?", (owner,))
        await db.execute("UPDATE channel_profiles SET is_active=1, updated_at=? WHERE owner_id=? AND id=?", (datetime.utcnow().isoformat(timespec='seconds'), owner, int(profile_id)))
        await db.commit()
    profile = await get_active_channel_profile(owner_id=owner)
    if profile:
        await set_setting("channel_target", profile.get("channel_target", ""), owner_id=owner)
        await set_setting("topic", profile.get("topic", ""), owner_id=owner)
    return profile


async def sync_channel_profile_topic(owner_id: int | None, channel_target: str, topic: str):
    owner = int(owner_id or 0)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE channel_profiles SET topic=?, updated_at=? WHERE owner_id=? AND channel_target=?",
            ((topic or "").strip(), datetime.utcnow().isoformat(timespec='seconds'), owner, (channel_target or '').strip()),
        )
        await db.commit()
