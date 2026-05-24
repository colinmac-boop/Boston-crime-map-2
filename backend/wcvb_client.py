"""WCVB local-crime story client.

Keeps WCVB narrative stories as source-attributed records separate from
structured BPD open-data incidents. Starts with explicitly seeded WCVB stories
Colin asks to add, so the records survive cache refreshes/deploys.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from geocode import geocode

logger = logging.getLogger(__name__)

SOURCE_ROOT = "https://www.wcvb.com"
CACHE_TTL = timedelta(hours=1)
SEED_URLS = [
    "https://www.wcvb.com/article/downtown-crossing-child-assault-investigation-may-19-2026/71352602",
    "https://www.wcvb.com/article/boston-roxbury-shooting-man-hospitalized/71288127",
    # 2026-05-24: Arrest in Dacia St (Dorchester) shooting; Chivaugn Nettles.
    "https://www.wcvb.com/article/boston-dorchester-dacia-st-shooting-arrest/71392346",
    # 2026-05-20: BPD Officer O'Malley indicted on voluntary manslaughter
    # charge in Dorchester/Roxbury shooting death; police-accountability.
    "https://www.wcvb.com/article/boston-officer-omalley-king-shooting-voluntary-manslaughter-dorchester/71362872",
    # 2026-05-20: Body-cam video from 2020 BPD shootout with Tyler Brown.
    "https://www.wcvb.com/article/tyler-brown-boston-police-body-cam-video-2020/71366182",
]

BOSTON_NEIGHBORHOODS = (
    "Boston", "Dorchester", "Mattapan", "Jamaica Plain", "Roxbury", "Hyde Park",
    "East Boston", "South Boston", "Charlestown", "Back Bay", "Fenway",
    "Allston", "Brighton", "West Roxbury", "Roslindale", "South End",
    "Downtown", "Chinatown", "Beacon Hill", "North End", "Mission Hill",
    "Seaport", "Fort Point", "Longwood",
)

STREET_RE = re.compile(
    r"\b(?:area of|near|on)\s+(?P<street>[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))\b",
    re.I,
)

INTERSECTION_RE = re.compile(
    r"\bintersection of\s+(?P<a>[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))\s+and\s+"
    r"(?P<b>[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))\b",
    re.I,
)

CATEGORY_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("shooting", ("shooting", "shot", "gunshot", "gunfire", "shots were fired", "firearm")),
    ("homicide", ("homicide", "murder", "manslaughter", "killed", "pronounced dead")),
    ("assault", ("stabbing", "stabbed", "slashing", "assault", "battery")),
    ("robbery", ("robbery",)),
    ("burglary", ("burglary", "break-in")),
    ("vehicle_theft", ("stolen car", "auto theft", "carjacking")),
]


def _strip_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _json_ld(html_text: str) -> dict[str, Any]:
    for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.S | re.I):
        try:
            data = json.loads(html.unescape(m.group(1)).strip())
        except Exception:
            continue
        if isinstance(data, dict) and "NewsArticle" in str(data.get("@type", "")):
            return data
    return {}


def _parse_date(raw: str | None) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _category(title: str, body: str) -> str:
    text = f"{title} {body}".lower()
    for category, patterns in CATEGORY_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return category
    return "other"


def _bucket(category: str) -> str:
    if category in {"homicide", "shooting", "robbery", "assault"}:
        return "violent"
    if category in {"burglary", "larceny", "vehicle_theft", "vandalism"}:
        return "property"
    return "other"


def _neighborhood(text: str) -> str:
    hits = []
    for neighborhood in [n for n in BOSTON_NEIGHBORHOODS if n != "Boston"]:
        m = re.search(rf"\b{re.escape(neighborhood)}\b", text, re.I)
        if m:
            hits.append((m.start(), neighborhood))
    if hits:
        return sorted(hits)[0][1]
    return "Boston"


def _canonical_street(street: str) -> str:
    street = re.sub(r"\s+", " ", street).strip()
    street = re.sub(r"\bSt\.?$", "Street", street, flags=re.I)
    street = re.sub(r"\bAve\.?$", "Avenue", street, flags=re.I)
    street = re.sub(r"\bRd\.?$", "Road", street, flags=re.I)
    return street


def _extract_street(text: str) -> Optional[str]:
    if re.search(r"\bDowntown Crossing\b", text, re.I) and re.search(r"\bMacy'?s\b", text, re.I):
        # WCVB's May 19, 2026 Downtown Crossing story describes officers outside
        # Macy's near Chauncey/Summer; Nominatim resolves the storefront reliably
        # while the street-intersection phrase does not.
        return "450 Washington Street"
    intersection = INTERSECTION_RE.search(text)
    if intersection:
        a = _canonical_street(intersection.group("a"))
        b = _canonical_street(intersection.group("b"))
        return f"{a} & {b}"
    m = STREET_RE.search(text)
    if not m:
        return None
    return _canonical_street(m.group("street"))


def _summary(title: str, body: str) -> str:
    first = re.split(r"(?<=[.!?])\s+", body.strip())[0] if body.strip() else title
    return first if len(first) <= 280 else first[:277].rstrip() + "…"


def _is_boston_crime(title: str, body: str) -> bool:
    text = f"{title} {body}"
    low = text.lower()
    if not any(word in low for word in ("shooting", "shot", "gunshot", "stabbing", "assault", "robbery", "arrest")):
        return False
    return any(re.search(rf"\b{re.escape(n)}\b", text, re.I) for n in BOSTON_NEIGHBORHOODS)


async def _fetch_article(client: httpx.AsyncClient, url: str) -> Optional[dict[str, Any]]:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        logger.warning("WCVB story fetch failed for %s: %s", url, exc)
        return None

    page = response.text
    ld = _json_ld(page)
    title = (ld.get("headline") or ld.get("name") or "").strip()
    body = (ld.get("articleBody") or ld.get("description") or _strip_tags(page)).strip()
    if not title or not _is_boston_crime(title, body):
        return None

    published = _parse_date(ld.get("datePublished") or ld.get("dateModified"))
    neighborhood = _neighborhood(f"{title} {body}")
    street = _extract_street(f"{title}. {body}") or neighborhood
    category = _category(title, body)
    story_id = hashlib.sha1(url.encode()).hexdigest()[:16]
    out: dict[str, Any] = {
        "story_id": story_id,
        "incident_number": f"wcvb-story-{story_id}",
        "source_type": "wcvb",
        "source_name": "WCVB",
        "source_url": url,
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
        "street": street,
        "district": "UNK",
        "neighborhood": neighborhood,
        "shooting": category == "shooting",
        "mappable": False,
        "attribution": "WCVB",
    }
    if street and street != neighborhood:
        out["address"] = f"{street}, {neighborhood}, Boston, MA" if neighborhood != "Boston" else f"{street}, Boston, MA"
    return out


async def fetch_recent_wcvb() -> list[dict[str, Any]]:
    headers = {"User-Agent": "BostonCrimeMap/1.0 (civic data publication)"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        stories = []
        for url in SEED_URLS:
            story = await _fetch_article(client, url)
            if story:
                stories.append(story)
        return stories


async def refresh_wcvb_cache(db) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    logger.info("WCVB crime refresh starting")
    stories = await fetch_recent_wcvb()
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
        await db.wcvb_stories.delete_many({})
        await db.wcvb_stories.insert_many(stories)
        for field in ("occurred_ts", "category", "mappable"):
            try:
                await db.wcvb_stories.create_index(field)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping optional WCVB story index %s: %s", field, exc)

    meta = {
        "_id": "wcvb_cache",
        "last_refreshed": started.isoformat(),
        "record_count": len(stories),
        "mappable_count": sum(1 for story in stories if story.get("mappable")),
        "source": SOURCE_ROOT,
        "attribution": "WCVB",
    }
    await db.cache_meta.replace_one({"_id": "wcvb_cache"}, meta, upsert=True)
    logger.info("WCVB crime refresh complete: %s stories", len(stories))
    return meta


async def ensure_wcvb_fresh(db) -> dict[str, Any]:
    meta = await db.cache_meta.find_one({"_id": "wcvb_cache"})
    if meta:
        try:
            last = datetime.fromisoformat(meta["last_refreshed"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return meta
        except (KeyError, ValueError):
            pass
    try:
        return await refresh_wcvb_cache(db)
    except Exception as exc:  # pragma: no cover
        logger.exception("WCVB crime refresh failed: %s", exc)
        return meta or {"_id": "wcvb_cache", "record_count": 0, "error": str(exc)}
