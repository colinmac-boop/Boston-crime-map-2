"""Universal Hub crime RSS client.

Universal Hub's HTML index is Cloudflare-protected in some environments, but its
Crime taxonomy RSS feed is reachable and includes article text, links, dates,
and neighborhood tags. We cache it as an attributed narrative source separate
from official BPD data.
"""
from __future__ import annotations

import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional

import httpx

from geocode import geocode

logger = logging.getLogger(__name__)

SOURCE_ROOT = "https://www.universalhub.com/crime/index.html"
FEED_URL = "https://www.universalhub.com/taxonomy/term/125/feed"
CACHE_TTL = timedelta(hours=1)
MAX_ITEMS = 14

ADDRESS_RE = re.compile(
    r"\b(?P<addr>\d{1,5}\s+[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))",
    re.I,
)

NEIGHBORHOODS = (
    "Dorchester", "Mattapan", "Jamaica Plain", "Roxbury", "Hyde Park",
    "East Boston", "South Boston", "Charlestown", "Back Bay", "Fenway",
    "Allston", "Brighton", "West Roxbury", "Roslindale", "South End",
    "Downtown", "Chinatown", "Beacon Hill", "North End", "Mission Hill",
    "Longwood", "Seaport", "Commonwealth Avenue Mall",
)

CATEGORY_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("shooting", ("shooting", "shot", "gunfire", "gun violence")),
    ("homicide", ("homicide", "murder", "manslaughter", "death of")),
    ("robbery", ("robbery", "mugging")),
    ("assault", ("assault", "battery", "ran down", "threw something", "attacked")),
    ("burglary", ("burglary", "break-in", "breaking into")),
    ("vehicle_theft", ("stolen car", "auto theft", "carjacking", "vehicle")),
    ("drugs", ("fentanyl", "cocaine", "drug", "narcotic")),
    ("larceny", ("stealing", "stole", "theft", "larceny")),
]


def _strip_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _category(title: str, body: str) -> str:
    text = f"{title} {body}".lower()
    for cat, pats in CATEGORY_PATTERNS:
        if any(p in text for p in pats):
            return cat
    return "other"


def _bucket(category: str) -> str:
    if category in {"homicide", "shooting", "robbery", "assault"}:
        return "violent"
    if category in {"burglary", "larceny", "vehicle_theft", "vandalism"}:
        return "property"
    if category == "drugs":
        return "drugs"
    return "other"


def _neighborhood(text: str) -> str:
    for n in NEIGHBORHOODS:
        if re.search(rf"\b{re.escape(n)}\b", text, re.I):
            if n == "Commonwealth Avenue Mall":
                return "Back Bay"
            return n
    return "Boston"


def _extract_neighborhood_from_description(desc_html: str) -> Optional[str]:
    m = re.search(r"Neighborhoods:&(?:nbsp;)?\s*</div>\s*<div[^>]*>\s*<div[^>]*>\s*<a[^>]*>(.*?)</a>", desc_html, re.S | re.I)
    if m:
        return _strip_tags(m.group(1))
    return None


def _extract_address(text: str) -> Optional[str]:
    m = ADDRESS_RE.search(text)
    if not m:
        return None
    addr = re.sub(r"\s+", " ", m.group("addr")).strip()
    addr = re.sub(r"\bSt\.?$", "Street", addr, flags=re.I)
    addr = re.sub(r"\bAve\.?$", "Avenue", addr, flags=re.I)
    addr = re.sub(r"\bRd\.?$", "Road", addr, flags=re.I)
    return addr


def _parse_date(raw: str | None) -> datetime:
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _summary(title: str, body: str) -> str:
    clean = body.strip()
    first = re.split(r"(?<=[.!?])\s+", clean)[0] if clean else title
    if len(first) > 280:
        first = first[:277].rstrip() + "…"
    return first


async def fetch_recent_universal_hub() -> list[dict[str, Any]]:
    headers = {"User-Agent": "BostonCrimeMap/1.0 (civic data publication)"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        r = await client.get(FEED_URL)
        r.raise_for_status()
        xml_text = r.text

    root = ET.fromstring(xml_text)
    items: list[dict[str, Any]] = []
    for item in root.findall("./channel/item")[:MAX_ITEMS]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc_html = item.findtext("description") or ""
        body = _strip_tags(desc_html)
        published = _parse_date(item.findtext("pubDate"))
        guid = (item.findtext("guid") or link or title).strip()
        story_id = hashlib.sha1(guid.encode()).hexdigest()[:16]
        neighborhood = _extract_neighborhood_from_description(desc_html) or _neighborhood(f"{title} {body}")
        address = _extract_address(f"{title}. {body}")
        category = _category(title, body)
        out: dict[str, Any] = {
            "story_id": story_id,
            "incident_number": f"uh-story-{story_id}",
            "source_type": "universal_hub",
            "source_name": "Universal Hub Crime",
            "source_url": link,
            "source_index_url": SOURCE_ROOT,
            "title": title,
            "headline": title,
            "description": title,
            "narrative": _summary(title, body),
            "excerpt": body[:320],
            "category": category,
            "bucket": _bucket(category),
            "published_on": published.isoformat(),
            "occurred_on": published.isoformat(),
            "occurred_ts": int(published.timestamp()),
            "street": address or neighborhood or "Boston",
            "district": "UNK",
            "neighborhood": neighborhood or "Boston",
            "shooting": category == "shooting",
            "mappable": False,
            "attribution": "Universal Hub",
        }
        if address:
            out["address"] = f"{address}, {neighborhood}, Boston, MA" if neighborhood and neighborhood != "Boston" else f"{address}, Boston, MA"
        items.append(out)
    return items


async def refresh_universal_hub_cache(db) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    logger.info("Universal Hub crime refresh starting")
    stories = await fetch_recent_universal_hub()
    for story in stories:
        address = story.get("address")
        if address:
            hit = await geocode(db, address)
            if hit:
                story["lat"] = hit["lat"]
                story["lng"] = hit["lng"]
                story["geocode_label"] = hit.get("label")
                story["mappable"] = True
        story.setdefault("lat", None)
        story.setdefault("lng", None)

    if stories:
        await db.universal_hub_stories.delete_many({})
        await db.universal_hub_stories.insert_many(stories)
        for field in ("occurred_ts", "category", "mappable"):
            try:
                await db.universal_hub_stories.create_index(field)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping optional Universal Hub story index %s: %s", field, exc)

    meta = {
        "_id": "universal_hub_cache",
        "last_refreshed": started.isoformat(),
        "record_count": len(stories),
        "mappable_count": sum(1 for s in stories if s.get("mappable")),
        "source": SOURCE_ROOT,
        "feed": FEED_URL,
        "attribution": "Universal Hub",
    }
    await db.cache_meta.replace_one({"_id": "universal_hub_cache"}, meta, upsert=True)
    logger.info("Universal Hub crime refresh complete: %s stories", len(stories))
    return meta


async def ensure_universal_hub_fresh(db) -> dict[str, Any]:
    meta = await db.cache_meta.find_one({"_id": "universal_hub_cache"})
    if meta:
        try:
            last = datetime.fromisoformat(meta["last_refreshed"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return meta
        except (KeyError, ValueError):
            pass
    try:
        return await refresh_universal_hub_cache(db)
    except Exception as exc:  # pragma: no cover
        logger.exception("Universal Hub crime refresh failed: %s", exc)
        return meta or {"_id": "universal_hub_cache", "record_count": 0, "error": str(exc)}
