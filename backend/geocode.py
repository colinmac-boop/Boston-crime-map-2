"""Geocoding via OpenStreetMap Nominatim.

No API key required, just a courteous User-Agent and respect for rate limits.
Results are cached in MongoDB so common queries don't re-hit Nominatim.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "BostonCrimeMap/1.0 (civic data publication)"

# Greater Boston bounding box (west, south, east, north). Anything outside
# this returns no results — keeps users from accidentally getting matched to
# "Boston" in Lincolnshire, UK.
BOSTON_VIEWBOX = "-71.25,42.20,-70.90,42.45"

CACHE_TTL = timedelta(days=30)


async def geocode(db, query: str) -> dict[str, Any] | None:
    """Return the best Boston-area match for `query` or None."""
    q = (query or "").strip()
    if not q:
        return None

    norm = q.lower()
    cached = await db.geocode_cache.find_one({"_id": norm})
    if cached:
        try:
            last = datetime.fromisoformat(cached["cached_at"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return cached.get("result")
        except (KeyError, ValueError):
            pass

    # Append "Boston, MA" if the user didn't include a city, to help Nominatim.
    if "boston" not in norm and "ma" not in norm and "," not in q:
        q_full = f"{q}, Boston, MA"
    else:
        q_full = q

    params = {
        "q": q_full,
        "format": "json",
        "addressdetails": "1",
        "limit": "1",
        "viewbox": BOSTON_VIEWBOX,
        "bounded": "1",
        "countrycodes": "us",
    }
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(NOMINATIM_URL, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # pragma: no cover - upstream flakiness
        logger.warning("Nominatim error for %r: %s", q, exc)
        return None

    if not data:
        # Cache the miss too — for 1 day, so we don't keep retrying bad queries.
        await db.geocode_cache.replace_one(
            {"_id": norm},
            {
                "_id": norm,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "result": None,
            },
            upsert=True,
        )
        return None

    hit = data[0]
    try:
        lat = float(hit["lat"])
        lng = float(hit["lon"])
    except (KeyError, ValueError):
        return None

    result = {
        "lat": lat,
        "lng": lng,
        "display_name": hit.get("display_name", q),
        "label": _short_label(hit),
        "type": hit.get("type"),
        "class": hit.get("class"),
    }

    await db.geocode_cache.replace_one(
        {"_id": norm},
        {
            "_id": norm,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
        },
        upsert=True,
    )
    return result


def _short_label(hit: dict[str, Any]) -> str:
    addr = hit.get("address", {}) or {}
    parts: list[str] = []
    house = addr.get("house_number")
    road = addr.get("road")
    if house and road:
        parts.append(f"{house} {road}")
    elif road:
        parts.append(road)
    nb = addr.get("neighbourhood") or addr.get("suburb") or addr.get("quarter")
    if nb:
        parts.append(nb)
    if not parts:
        return hit.get("display_name", "").split(",")[0]
    return " · ".join(parts)


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in miles. Plenty accurate for city-scale work."""
    from math import asin, cos, radians, sin, sqrt

    r_mi = 3958.7613
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r_mi * asin(sqrt(a))
