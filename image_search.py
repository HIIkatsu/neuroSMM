
import httpx
import os
import random

PEXELS_URL = "https://api.pexels.com/v1/search"

async def find_image(query: str) -> str | None:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return None

    params = {
        "query": query,
        "per_page": 20,
        "orientation": "landscape"
    }

    headers = {
        "Authorization": api_key
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(PEXELS_URL, headers=headers, params=params)

        if r.status_code != 200:
            return None

        data = r.json()
        photos = data.get("photos") or []

        if not photos:
            return None

        photo = random.choice(photos)

        src = photo.get("src", {})

        return src.get("large2x") or src.get("large") or src.get("original")

    except Exception:
        return None
