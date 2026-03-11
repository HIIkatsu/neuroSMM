from __future__ import annotations

import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx
import trafilatura

import db
from content import generate_post_text


def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _topic_default_sources(topic: str) -> str:
    topic_l = (topic or "").lower()

    if any(x in topic_l for x in [
        "чип", "чипов", "полупровод", "микросх", "semiconductor",
        "chip", "chips", "tsmc", "intel", "amd", "nvidia", "fab", "литограф"
    ]):
        return ",".join([
            "reuters.com",
            "bloomberg.com",
            "anandtech.com",
            "tomshardware.com",
            "techpowerup.com",
            "semiengineering.com",
            "eetimes.com",
        ])

    if any(x in topic_l for x in [
        "ии", "ai", "openai", "нейросет", "машинное обучение",
        "gpt", "llm", "искусственный интеллект"
    ]):
        return ",".join([
            "reuters.com",
            "theverge.com",
            "techcrunch.com",
            "arstechnica.com",
            "wired.com",
        ])

    if any(x in topic_l for x in [
        "игр", "game", "gaming", "steam", "playstation", "xbox", "nintendo"
    ]):
        return ",".join([
            "ign.com",
            "gamespot.com",
            "pcgamer.com",
            "eurogamer.net",
            "theverge.com",
        ])

    if any(x in topic_l for x in [
        "массаж", "здоров", "меди", "ожир", "спин", "шея",
        "восстанов", "лечен", "болез", "врач", "физиотерап"
    ]):
        return ",".join([
            "who.int",
            "mayoclinic.org",
            "nih.gov",
            "medicalnewstoday.com",
            "sciencedaily.com",
        ])

    if any(x in topic_l for x in [
        "финанс", "акци", "рынок", "доллар", "бирж", "инвест", "эконом"
    ]):
        return ",".join([
            "reuters.com",
            "bloomberg.com",
            "cnbc.com",
            "wsj.com",
            "ft.com",
        ])

    return ",".join([
        "reuters.com",
        "bbc.com",
        "bloomberg.com",
        "apnews.com",
    ])


def _build_rss_url(topic: str, sources: list[str]) -> str:
    topic = (topic or "").strip()
    query = topic or "latest news"

    if sources:
        source_expr = " OR ".join([f"site:{s.strip()}" for s in sources if s.strip()])
        query = f"{query} ({source_expr})"

    encoded = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=ru&gl=RU&ceid=RU:ru"


async def _extract_article_text_and_image(url: str) -> tuple[str, str]:
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            r = await client.get(url)

        if r.status_code != 200:
            return "", ""

        html_text = r.text or ""

        article_text = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            output_format="txt",
        ) or ""

        og_image = ""

        m = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            html_text,
            flags=re.I,
        )
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                html_text,
                flags=re.I,
            )
        if m:
            og_image = m.group(1).strip()

        return article_text.strip(), og_image.strip()

    except Exception:
        return "", ""


async def fetch_latest_news(owner_id: int = 0) -> dict | None:
    topic = (
        await db.get_setting("news_topic", owner_id=owner_id)
        or await db.get_setting("topic", owner_id=owner_id)
        or ""
    ).strip()

    if not topic:
        return None

    raw_sources = (
        await db.get_setting("news_sources", owner_id=owner_id)
        or _topic_default_sources(topic)
    )
    sources = [s.strip() for s in raw_sources.split(",") if s.strip()]

    urls = [
        _build_rss_url(topic, sources),  # сначала trusted sources
        _build_rss_url(topic, []),       # fallback: вообще без site:
    ]

    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
                r = await client.get(url)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.text)
        except Exception:
            continue

        channel = root.find("channel")
        if channel is None:
            continue

        for item in channel.findall("item"):
            title = _clean(item.findtext("title", ""))
            link = (item.findtext("link", "") or "").strip()
            description = _clean(item.findtext("description", ""))

            if not link or not title:
                continue

            if await db.is_news_used(link, owner_id=owner_id):
                continue

            article_text, image_url = await _extract_article_text_and_image(link)

            # если trusted-поиск дал совсем мусор без текста — позволяем fallback-итерации сработать
            if url == urls[0] and not article_text and len(urls) > 1:
                continue

            return {
                "title": title,
                "link": link,
                "description": description[:400],
                "topic": topic,
                "sources": sources,
                "article_text": article_text[:5000],
                "image_url": image_url,
            }

    return None


async def build_news_post(config, news_item: dict, owner_id: int = 0) -> str:
    title = news_item.get("title", "")
    description = news_item.get("description", "")
    topic = news_item.get("topic", "")
    link = news_item.get("link", "")
    article_text = (news_item.get("article_text") or "").strip()
    domain = urlparse(link).netloc

    if article_text:
        prompt = (
            f"Сделай краткий телеграм-пост в 3-5 абзацев по свежей новости на тему '{topic}'. "
            f"Используй ТОЛЬКО факты из текста статьи ниже. "
            f"Ничего не придумывай, не додумывай причины, последствия и цифры. "
            f"Если данных мало, напиши только то, что точно есть.\n\n"
            f"Заголовок: {title}\n"
            f"Текст статьи:\n{article_text}\n\n"
            f"В конце добавь строку: Источник: {domain}"
        )
    else:
        prompt = (
            f"Сделай очень краткий телеграм-пост по свежей новости на тему '{topic}'. "
            f"Используй только то, что есть в заголовке и описании. "
            f"Ничего не придумывай.\n\n"
            f"Заголовок: {title}\n"
            f"Описание: {description}\n\n"
            f"В конце добавь строку: Источник: {domain}"
        )

    return await generate_post_text(
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
        topic=topic,
        prompt=prompt,
        base_url=getattr(config, "openrouter_base_url", None),
    )