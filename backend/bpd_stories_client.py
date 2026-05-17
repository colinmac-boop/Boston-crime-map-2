"""Boston Police Department narrative story client.

Pulls recent posts from police.boston.gov/stories-in-the-news, filters for
crime/public-safety narrative items, extracts an incident-ish location when the
article provides one, and caches the result separately from the structured BPD
open-data feed.

These posts are intentionally treated as a second source: useful for current
context while BPD open data is stale, but not a replacement for structured
incident records.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx

from geocode import geocode

logger = logging.getLogger(__name__)

SOURCE_ROOT = "https://police.boston.gov/stories-in-the-news/"
CACHE_TTL = timedelta(hours=1)
MAX_PAGES = 2
MAX_ARTICLES = 18
ET = ZoneInfo("America/New_York")

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

CRIME_KEYWORDS = (
    "arrest", "arrested", "suspect", "firearm", "gun", "shooting", "shotspotter",
    "homicide", "murder", "robbery", "assault", "battery", "home invasion",
    "burglary", "larceny", "stolen", "recovered", "drug", "moped", "drink spiking",
    "community alert", "victim",
)

EXCLUDE_TITLE_KEYWORDS = (
    "boston 24 and public journal",
    "bpd in the community",
    "remembers the service",
    "peace officers memorial",
    "mental health awareness",
    "missing person",
    "cancel missing person",
)

ADDRESS_RE = re.compile(
    r"\b(?:at|area of|near|outside of|responded to|located at)\s+(?:the\s+)?"
    r"(?P<addr>\d{1,5}\s+[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))",
    re.I,
)

NEIGHBORHOODS = (
    "Dorchester", "Mattapan", "Jamaica Plain", "Roxbury", "Hyde Park",
    "East Boston", "South Boston", "Charlestown", "Back Bay", "Fenway",
    "Allston", "Brighton", "West Roxbury", "Roslindale", "South End",
    "Downtown", "Chinatown", "Beacon Hill", "North End", "Mission Hill",
)

CATEGORY_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("homicide", ("homicide", "murder")),
    ("shooting", ("shooting", "shotspotter", "person shot", "gunshot")),
    ("robbery", ("robbery",)),
    ("assault", ("assault", "battery", "home invasion")),
    ("burglary", ("burglary", "breaking and entering")),
    ("vehicle_theft", ("stolen moped", "stolen vehicle", "auto theft", "receiving stolen property", "moped")),
    ("drugs", ("drug", "narcotic", "drink spiking", "rohypnol", "ghb", "ketamine")),
    ("larceny", ("larceny", "theft")),
]


def _strip_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _decode(raw: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", raw)).strip()


def _archive_pages() -> list[str]:
    return [SOURCE_ROOT] + [f"{SOURCE_ROOT}page/{i}/" for i in range(2, MAX_PAGES + 1)]


def _parse_archive(html_text: str) -> list[dict[str, str]]:
    posts: list[dict[str, str]] = []
    for block in re.findall(r"<article\b.*?</article>", html_text, flags=re.S | re.I):
        m = re.search(r'<h2[^>]*class="[^"]*entry-title[^"]*"[^>]*>\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S | re.I)
        if not m:
            continue
        url = html.unescape(m.group(1))
        title = _strip_tags(m.group(2))
        dm = re.search(r'<span[^>]*class="[^"]*published[^"]*"[^>]*>(.*?)</span>', block, flags=re.S | re.I)
        published = _strip_tags(dm.group(1)) if dm else ""
        em = re.search(r'<div[^>]*class="[^"]*ast-excerpt-container[^"]*"[^>]*>(.*?)</div>', block, flags=re.S | re.I)
        excerpt = _strip_tags(em.group(1)) if em else ""
        posts.append({"url": url, "title": title, "published_label": published, "excerpt": excerpt})
    return posts


def _is_candidate(post: dict[str, str]) -> bool:
    title = post.get("title", "").lower()
    text = f"{post.get('title','')} {post.get('excerpt','')}".lower()
    if any(x in title for x in EXCLUDE_TITLE_KEYWORDS):
        return False
    return any(k in text for k in CRIME_KEYWORDS)


def _parse_published(label: str, url: str) -> datetime:
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", label or "")
    if m:
        month, day, year = m.groups()
        return datetime(int(year), MONTHS[month.lower()], int(day), 12, 0, tzinfo=ET).astimezone(timezone.utc)
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        y, mo, d = map(int, m.groups())
        return datetime(y, mo, d, 12, 0, tzinfo=ET).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _parse_story_time(text: str, fallback: datetime) -> datetime:
    # Examples: "At about 8:13 PM on Wednesday, May 13, 2026" or
    # "At approximately 2:10 p.m. on Tuesday, May 12, 2026".
    pattern = re.compile(
        r"(?:at\s+(?:about|approximately)\s+)?(\d{1,2}):(\d{2})\s*([ap])\.?m\.?.{0,80}?"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(\d{1,2}),\s+(\d{4})",
        re.I,
    )
    m = pattern.search(text)
    if not m:
        # Date only: "occurred ... April 20, 2026".
        dm = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})",
            text,
            re.I,
        )
        if not dm:
            return fallback
        month, day, year = dm.groups()
        return datetime(int(year), MONTHS[month.lower()], int(day), 12, 0, tzinfo=ET).astimezone(timezone.utc)
    hour, minute, ap, month, day, year = m.groups()
    h = int(hour) % 12
    if ap.lower() == "p":
        h += 12
    dt = datetime(int(year), MONTHS[month.lower()], int(day), h, int(minute), tzinfo=ET)
    return dt.astimezone(timezone.utc)


def _category(title: str, body: str) -> str:
    text = f"{title} {body}".lower()
    for cat, pats in CATEGORY_PATTERNS:
        if any(p in text for p in pats):
            return cat
    return "other"


def _neighborhood(text: str) -> str:
    for n in NEIGHBORHOODS:
        if re.search(rf"\b{re.escape(n)}\b", text, re.I):
            return n
    return "Boston"


def _district(text: str) -> str:
    m = re.search(r"District\s+([A-E])[- ]?(\d{1,2})", text, re.I)
    if m:
        return f"{m.group(1).upper()}{m.group(2)}"
    return "UNK"


def _extract_address(text: str) -> Optional[str]:
    m = ADDRESS_RE.search(text)
    if not m:
        return None
    addr = re.sub(r"\s+", " ", m.group("addr")).strip()
    # Normalize common abbreviated endings enough for display/geocoding.
    addr = re.sub(r"\bSt\.?$", "Street", addr, flags=re.I)
    addr = re.sub(r"\bAve\.?$", "Avenue", addr, flags=re.I)
    addr = re.sub(r"\bRd\.?$", "Road", addr, flags=re.I)
    return addr


def _summary(title: str, body: str, category: str, neighborhood: str) -> str:
    first = re.split(r"(?<=[.!?])\s+", body.strip())[0] if body.strip() else title
    first = re.sub(r"^Keeping Boston Safe:\s*", "", first, flags=re.I)
    if len(first) > 260:
        first = first[:257].rstrip() + "…"
    if "drink spiking" in title.lower():
        return "BPD warned residents and college-event crowds about drink spiking and urged victims to report incidents promptly."
    return first


async def _fetch_article(client: httpx.AsyncClient, post: dict[str, str]) -> dict[str, Any]:
    published = _parse_published(post.get("published_label", ""), post["url"])
    title = post["title"]
    body = post.get("excerpt", "")
    try:
        r = await client.get(post["url"])
        r.raise_for_status()
        page = r.text
        content = re.search(r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>\s*</div>', page, flags=re.S | re.I)
        if content:
            body = _strip_tags(content.group(1))
        else:
            # Good enough fallback: readability-like body after title.
            body = _strip_tags(page)
    except Exception as exc:  # pragma: no cover - source flakiness
        logger.warning("BPD story fetch failed for %s: %s", post["url"], exc)

    full_text = f"{title}. {body}"
    category = _category(title, body)
    neighborhood = _neighborhood(full_text)
    address = _extract_address(full_text)
    occurred = _parse_story_time(full_text, published)
    story_id = hashlib.sha1(post["url"].encode()).hexdigest()[:16]
    out: dict[str, Any] = {
        "story_id": story_id,
        "incident_number": f"bpd-story-{story_id}",
        "source_type": "bpd_story",
        "source_name": "Boston Police Department Stories in the News",
        "source_url": post["url"],
        "title": title,
        "headline": title,
        "description": title,
        "narrative": _summary(title, body, category, neighborhood),
        "excerpt": post.get("excerpt") or body[:300],
        "category": category,
        "bucket": "violent" if category in {"homicide", "shooting", "robbery", "assault"} else ("property" if category in {"burglary", "larceny", "vehicle_theft", "vandalism"} else ("drugs" if category == "drugs" else "other")),
        "published_on": published.isoformat(),
        "occurred_on": occurred.isoformat(),
        "occurred_ts": int(occurred.timestamp()),
        "street": address or neighborhood,
        "district": _district(full_text),
        "neighborhood": neighborhood,
        "shooting": category == "shooting",
        "mappable": False,
    }
    if address:
        out["address"] = f"{address}, {neighborhood}, Boston, MA" if neighborhood != "Boston" else f"{address}, Boston, MA"
    return out


async def fetch_recent_stories() -> list[dict[str, Any]]:
    headers = {"User-Agent": "BostonCrimeMap/1.0 (civic data publication)"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        posts: list[dict[str, str]] = []
        for url in _archive_pages():
            r = await client.get(url)
            r.raise_for_status()
            posts.extend(_parse_archive(r.text))
        candidates = [p for p in posts if _is_candidate(p)]
        candidates = candidates[:MAX_ARTICLES]
        stories = await asyncio.gather(*[_fetch_article(client, p) for p in candidates])
    return list(stories)


async def refresh_stories_cache(db) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    logger.info("BPD stories refresh starting")
    stories = await fetch_recent_stories()

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
        await db.bpd_stories.delete_many({})
        await db.bpd_stories.insert_many(stories)
        for field in ("occurred_ts", "category", "mappable"):
            try:
                await db.bpd_stories.create_index(field)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping optional story index %s: %s", field, exc)

    meta = {
        "_id": "bpd_stories_cache",
        "last_refreshed": started.isoformat(),
        "record_count": len(stories),
        "mappable_count": sum(1 for s in stories if s.get("mappable")),
        "source": SOURCE_ROOT,
    }
    await db.cache_meta.replace_one({"_id": "bpd_stories_cache"}, meta, upsert=True)
    logger.info("BPD stories refresh complete: %s stories", len(stories))
    return meta


async def ensure_stories_fresh(db) -> dict[str, Any]:
    meta = await db.cache_meta.find_one({"_id": "bpd_stories_cache"})
    if meta:
        try:
            last = datetime.fromisoformat(meta["last_refreshed"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return meta
        except (KeyError, ValueError):
            pass
    try:
        return await refresh_stories_cache(db)
    except Exception as exc:  # pragma: no cover
        logger.exception("BPD stories refresh failed: %s", exc)
        return meta or {"_id": "bpd_stories_cache", "record_count": 0, "error": str(exc)}


_stories_lock = asyncio.Lock()


async def ensure_stories_fresh_locked(db) -> dict[str, Any]:
    async with _stories_lock:
        return await ensure_stories_fresh(db)
