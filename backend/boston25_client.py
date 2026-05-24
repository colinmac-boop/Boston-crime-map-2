"""Boston 25 News local-crime story client.

Scrapes Boston 25's public homepage/local-news pages plus a small set of
known Boston crime URLs Colin explicitly pointed us toward. The site is broad
Massachusetts news, so this adapter is conservative: keep only crime/public-
safety items that appear to be inside Boston proper, then cache them as an
attributed narrative source separate from official BPD data.
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

SOURCE_ROOT = "https://www.boston25news.com"
LOCAL_URL = "https://www.boston25news.com/news/local/"
CACHE_TTL = timedelta(hours=1)
MAX_LINKS = 30

# Explicit seeds from Colin's direction. Keep them durable even when they
# fall off the current homepage/local index. Add new Boston-proper stories
# here so they persist across cache refreshes.
SEED_URLS = [
    "https://www.boston25news.com/news/local/police-identify-man-killed-in-boston-stabbing/AZN7KDAXC5G4LGC7KALA4R674M/",
    "https://www.boston25news.com/news/local/police-investigating-after-two-shot-overnight-dorchester/ZWQO5PP36BFB5FOI3MEFE7APYQ/",
    # 2026-05-21: Five charged in brawl inside Dorchester District Court (510 Washington St).
    "https://www.boston25news.com/news/local/5-people-arrested-after-brawl-breaks-out-boston-courthouse-police-say/KEAFL2A4S5C5LHIQX7JK5E43JM/",
    # 2026-05-22: Fatal overnight shooting on Bowdoin St in Dorchester.
    "https://www.boston25news.com/news/local/1-killed-following-overnight-shooting-dorchester/4Z2HC2BEQVBIZM4HEYIJ27ZMZY/",
    # 2026-05-23: Arrest in 25 Dacia St (Dorchester) shooting.
    "https://www.boston25news.com/news/local/boston-police-arrest-man-connection-with-dorchester-shooting-that-injured-one/EYUSKU5QG5F2JBBKVHXXWHIZ64/",
    # 2026-05-20: BPD Officer Nicholas O'Malley indicted on voluntary manslaughter
    # for Roxbury shooting death of carjacking suspect; police-accountability story.
    "https://www.boston25news.com/news/local/boston-police-officer-indicted-shooting-death-dorchester-man/V3TALRFXLND7ZKLWJLJVY5FAIM/",
]

CRIME_KEYWORDS = (
    "stabbing", "stabbed", "stab wounds", "slashing", "slashed", "shooting", "shot", "homicide",
    "murder", "manslaughter", "assault", "robbery", "arrest", "suspect",
    "firearm", "gun", "knife", "deadly",
)

BOSTON_NEIGHBORHOODS = (
    "Boston", "Dorchester", "Mattapan", "Jamaica Plain", "Roxbury", "Hyde Park",
    "East Boston", "South Boston", "Charlestown", "Back Bay", "Fenway",
    "Allston", "Brighton", "West Roxbury", "Roslindale", "South End",
    "Downtown", "Chinatown", "Beacon Hill", "North End", "Mission Hill",
    "Seaport", "Fort Point", "Longwood",
)

OUTSIDE_PLACE_HINTS = (
    "Brockton", "Cambridge", "Danvers", "Lawrence", "Worcester", "New York",
    "Times Square", "Wellesley", "Vermont", "New Hampshire", "Gloucester",
    "Maine", "Beverly", "Lowell", "Springfield",
    # Common national/regional stories that bleed in through Boston 25's chyron
    # or related-story rails. Keep this Boston-only.
    "White House", "Washington, D.C.", "Washington DC", "San Diego", "Mexico",
    "Florida", "Texas", "California", "Ohio", "Connecticut", "Rhode Island",
    "Quincy", "Revere", "Chelsea", "Somerville", "Newton", "Medford", "Malden",
    "Saugus", "Lynn", "Salem", "Framingham", "Waltham",
)

ADDRESS_RE = re.compile(
    r"\b(?P<addr>\d{1,5}\s+[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))",
    re.I,
)
AREA_ADDRESS_RE = re.compile(
    r"\b(?:area of|near|at|on)\s+(?P<addr>\d{1,5}\s+[A-Z][A-Za-z0-9 .'-]+?\s+"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|"
    r"Terrace|Ter\.?|Court|Ct\.?|Place|Pl\.?|Lane|Ln\.?|Way))\b",
    re.I,
)

CATEGORY_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("shooting", ("shooting", "shot", "gunfire", "firearm")),
    ("homicide", ("homicide", "murder", "manslaughter", "killed", "deadly stabbing", "pronounced dead")),
    ("assault", ("stabbing", "stabbed", "stab wounds", "slashing", "slashed", "assault", "battery", "knife")),
    ("robbery", ("robbery",)),
    ("burglary", ("burglary", "break-in")),
    ("vehicle_theft", ("stolen car", "auto theft", "carjacking")),
    ("drugs", ("fentanyl", "cocaine", "drug", "narcotic")),
    ("larceny", ("stealing", "stole", "theft", "larceny")),
]


def _strip_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _abs_url(href: str) -> str:
    href = html.unescape(href or "").strip()
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"{SOURCE_ROOT}{href}"
    return f"{SOURCE_ROOT}/{href}"


def _parse_index(html_text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in re.finditer(r'<h[12][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_text, re.S | re.I):
        url = _abs_url(m.group(1))
        title = _strip_tags(m.group(2))
        if not title or url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "title": title})
    return out


def _json_ld(html_text: str) -> dict[str, Any]:
    for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.S | re.I):
        try:
            data = json.loads(html.unescape(m.group(1)).strip())
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") in {"NewsArticle", "Article"}:
            return data
    return {}


def _paragraph_text(html_text: str) -> str:
    parts = re.findall(r'<p[^>]*class="[^"]*body-paragraph[^"]*"[^>]*>(.*?)</p>', html_text, re.S | re.I)
    if not parts:
        parts = re.findall(r"<p[^>]*>(.*?)</p>", html_text, re.S | re.I)
    return " ".join(_strip_tags(p) for p in parts if _strip_tags(p))


def _parse_date(raw: str | None) -> datetime:
    if raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


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


def _clean_address(addr: str) -> Optional[str]:
    addr = re.sub(r"\s+", " ", addr).strip()
    if len(addr) > 80 or re.search(r"\b(a\.m\.|p\.m\.|when|crews|responded|incident|story|graduate)\b", addr, re.I):
        return None
    addr = re.sub(r"\bSt\.?$", "Street", addr, flags=re.I)
    addr = re.sub(r"\bAve\.?$", "Avenue", addr, flags=re.I)
    addr = re.sub(r"\bRd\.?$", "Road", addr, flags=re.I)
    if addr.lower() == "25 weather street":
        return None
    return addr


def _extract_address(text: str) -> Optional[str]:
    for pattern in (AREA_ADDRESS_RE, ADDRESS_RE):
        for m in pattern.finditer(text):
            cleaned = _clean_address(m.group("addr"))
            if cleaned:
                return cleaned
    return None


def _neighborhood(text: str) -> str:
    hits = []
    for n in [n for n in BOSTON_NEIGHBORHOODS if n != "Boston"]:
        m = re.search(rf"\b{re.escape(n)}\b", text, re.I)
        if m:
            hits.append((m.start(), n))
    if hits:
        return sorted(hits)[0][1]
    return "Boston"


def _looks_like_boston_story(title: str, body: str, url: str) -> bool:
    # Boston25 pages carry lots of related-link/footer text. Judge relevance
    # mostly from the headline and a short lead, not the entire page, so the
    # ever-present "Boston 25 News" brand text in the chyron does not let
    # national stories slip through.
    lead = body[:400]
    signal_text = f"{title} {lead}"
    low = signal_text.lower()
    if not any(k in low for k in CRIME_KEYWORDS):
        return False
    if "crash" in title.lower() and not re.search(r"\b(charged|arrest|indicted|manslaughter|homicide)\b", signal_text, re.I):
        return False
    outside_text = f"{title} {body[:400]}"
    if any(re.search(rf"\b{re.escape(place)}\b", outside_text, re.I) for place in OUTSIDE_PLACE_HINTS):
        # Allow explicit Boston story URLs to override generic outside hints in
        # related-link boilerplate, but otherwise keep the map Boston-only.
        if "boston-stabbing" not in url and "dorchester" not in low and "south boston" not in low:
            return False
    # Require a Boston neighborhood mention in title or short lead, not just
    # the bare word "Boston" (which is also the news-station brand).
    specific_neighborhoods = [n for n in BOSTON_NEIGHBORHOODS if n != "Boston"]
    if any(re.search(rf"\b{re.escape(n)}\b", signal_text, re.I) for n in specific_neighborhoods):
        return True
    # Fall back to "Boston" only when paired with a crime keyword in the title
    # itself (e.g. "Boston police arrest...", "Boston shooting"), not just
    # brand chrome.
    if re.search(r"\bBoston\b", title, re.I) and any(k in title.lower() for k in CRIME_KEYWORDS):
        return True
    return False


def _summary(title: str, body: str) -> str:
    first = re.split(r"(?<=[.!?])\s+", body.strip())[0] if body.strip() else title
    if len(first) > 280:
        first = first[:277].rstrip() + "…"
    return first


async def _fetch_article(client: httpx.AsyncClient, url: str, fallback_title: str = "") -> Optional[dict[str, Any]]:
    try:
        r = await client.get(url)
        r.raise_for_status()
    except Exception as exc:  # pragma: no cover
        logger.warning("Boston25 story fetch failed for %s: %s", url, exc)
        return None
    page = r.text
    ld = _json_ld(page)
    title = (ld.get("headline") or fallback_title or "").strip()
    body = _paragraph_text(page) or (ld.get("description") or "")
    if not _looks_like_boston_story(title, body, url):
        return None

    published = _parse_date(ld.get("datePublished") or ld.get("dateModified"))
    category = _category(title, body)
    neighborhood = _neighborhood(f"{title} {body}")
    address = _extract_address(f"{title}. {body}")
    story_id = hashlib.sha1(url.encode()).hexdigest()[:16]
    out: dict[str, Any] = {
        "story_id": story_id,
        "incident_number": f"boston25-story-{story_id}",
        "source_type": "boston25",
        "source_name": "Boston 25 News",
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
        "street": address or neighborhood,
        "district": "UNK",
        "neighborhood": neighborhood,
        "shooting": category == "shooting",
        "mappable": False,
        "attribution": "Boston 25 News",
    }
    if address:
        out["address"] = f"{address}, {neighborhood}, Boston, MA" if neighborhood != "Boston" else f"{address}, Boston, MA"
    return out


async def fetch_recent_boston25() -> list[dict[str, Any]]:
    headers = {"User-Agent": "BostonCrimeMap/1.0 (civic data publication)"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True) as client:
        links: list[dict[str, str]] = [{"url": u, "title": ""} for u in SEED_URLS]
        for index_url in (SOURCE_ROOT, LOCAL_URL):
            try:
                r = await client.get(index_url)
                r.raise_for_status()
                links.extend(_parse_index(r.text))
            except Exception as exc:  # pragma: no cover
                logger.warning("Boston25 index fetch failed for %s: %s", index_url, exc)
        seen: set[str] = set()
        unique = []
        for link in links:
            url = link["url"]
            if url in seen or "boston25news.com" not in url or "/weather/" in url:
                continue
            seen.add(url)
            unique.append(link)
        stories: list[dict[str, Any]] = []
        for link in unique[:MAX_LINKS]:
            story = await _fetch_article(client, link["url"], link.get("title", ""))
            if story:
                stories.append(story)
    return stories


async def refresh_boston25_cache(db) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    logger.info("Boston25 crime refresh starting")
    stories = await fetch_recent_boston25()
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
        await db.boston25_stories.delete_many({})
        await db.boston25_stories.insert_many(stories)
        for field in ("occurred_ts", "category", "mappable"):
            try:
                await db.boston25_stories.create_index(field)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping optional Boston25 story index %s: %s", field, exc)

    meta = {
        "_id": "boston25_cache",
        "last_refreshed": started.isoformat(),
        "record_count": len(stories),
        "mappable_count": sum(1 for s in stories if s.get("mappable")),
        "source": SOURCE_ROOT,
        "attribution": "Boston 25 News",
    }
    await db.cache_meta.replace_one({"_id": "boston25_cache"}, meta, upsert=True)
    logger.info("Boston25 crime refresh complete: %s stories", len(stories))
    return meta


async def ensure_boston25_fresh(db) -> dict[str, Any]:
    meta = await db.cache_meta.find_one({"_id": "boston25_cache"})
    if meta:
        try:
            last = datetime.fromisoformat(meta["last_refreshed"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return meta
        except (KeyError, ValueError):
            pass
    try:
        return await refresh_boston25_cache(db)
    except Exception as exc:  # pragma: no cover
        logger.exception("Boston25 crime refresh failed: %s", exc)
        return meta or {"_id": "boston25_cache", "record_count": 0, "error": str(exc)}
