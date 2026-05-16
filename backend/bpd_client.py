"""Boston Police Department open-data client.

Fetches incidents from data.boston.gov CKAN datastore, normalizes them, and
caches them in MongoDB. All downstream endpoints query Mongo, never the
upstream API directly, so we are kind to BPD's servers and the page never
stalls.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# 2023-to-present resource. Verified 262k+ records, fields include Lat, Long,
# OFFENSE_DESCRIPTION, DISTRICT, OCCURRED_ON_DATE, SHOOTING.
RESOURCE_ID = "b973d8cb-eeb2-4e7e-99da-c92938efc9c0"
CKAN_URL = "https://data.boston.gov/api/3/action/datastore_search_sql"

CACHE_TTL = timedelta(hours=1)
FETCH_LIMIT = 8000  # Pull the most recent N rows on refresh.

# District code -> human label. Source: BPD district map.
DISTRICTS: dict[str, str] = {
    "A1": "Downtown / Beacon Hill / Chinatown / North End",
    "A15": "Charlestown",
    "A7": "East Boston",
    "B2": "Roxbury / Mission Hill",
    "B3": "Mattapan",
    "C6": "South Boston",
    "C11": "Dorchester",
    "D4": "Back Bay / Fenway / South End",
    "D14": "Allston / Brighton",
    "E5": "West Roxbury / Roslindale",
    "E13": "Jamaica Plain",
    "E18": "Hyde Park",
}


def categorize(desc: str | None, shooting: str | int | None) -> str:
    """Map BPD's messy OFFENSE_DESCRIPTION into clean categories."""
    if shooting and str(shooting) == "1":
        return "shooting"
    if not desc:
        return "other"
    d = desc.upper()
    if "HOMICIDE" in d or "MURDER" in d or "MANSLAUGHTER" in d:
        return "homicide"
    if "ROBBERY" in d:
        return "robbery"
    if "ASSAULT" in d:
        return "assault"
    if "BURGLARY" in d or "BREAKING AND ENTERING" in d or "B&E" in d:
        return "burglary"
    if "AUTO THEFT" in d or ("MOTOR VEHICLE" in d and ("THEFT" in d or "STOLEN" in d or "RECOVERED" in d)):
        return "vehicle_theft"
    if "LARCENY" in d or ("THEFT" in d and "MOTOR" not in d):
        return "larceny"
    if "VANDAL" in d or "PROPERTY DAMAGE" in d or "GRAFFITI" in d:
        return "vandalism"
    if "DRUG" in d or "NARCOTIC" in d:
        return "drugs"
    return "other"


CATEGORY_BUCKET = {
    "homicide": "violent",
    "shooting": "violent",
    "robbery": "violent",
    "assault": "violent",
    "burglary": "property",
    "larceny": "property",
    "vehicle_theft": "property",
    "vandalism": "property",
    "drugs": "drugs",
    "other": "other",
}


def _parse_date(raw: str | None) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    # Examples seen: "2023-01-27 22:44:00+00", "2024-08-12 09:15:00"
    raw = raw.replace("+00", "+00:00") if raw.endswith("+00") else raw
    fmts = [
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for f in fmts:
        try:
            dt = datetime.strptime(raw, f)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _clean_street(raw: str | None) -> str:
    if not raw:
        return ""
    return re.sub(r"\s+", " ", raw).strip().title()


def normalize(rec: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Convert a raw CKAN record to our shape; return None to drop."""
    try:
        lat = float(rec.get("Lat") or 0)
        lng = float(rec.get("Long") or 0)
    except (TypeError, ValueError):
        return None
    # BPD redacts some coords as 0,0 or -1,-1. Drop them.
    if not lat or not lng or abs(lat) < 1 or abs(lng) < 1:
        return None
    if not (41.5 < lat < 43.0 and -71.5 < lng < -70.5):  # rough Boston box
        return None

    occurred = _parse_date(rec.get("OCCURRED_ON_DATE"))
    desc = (rec.get("OFFENSE_DESCRIPTION") or "").strip()
    district = (rec.get("DISTRICT") or "").strip() or "UNK"
    category = categorize(desc, rec.get("SHOOTING"))

    return {
        "incident_number": (rec.get("INCIDENT_NUMBER") or "").strip(),
        "offense_code": (rec.get("OFFENSE_CODE") or "").strip(),
        "description": desc.title(),
        "description_raw": desc,
        "district": district,
        "shooting": str(rec.get("SHOOTING") or "0") == "1",
        "occurred_on": occurred.isoformat() if occurred else None,
        "occurred_ts": int(occurred.timestamp()) if occurred else 0,
        "year": int(rec.get("YEAR")) if rec.get("YEAR") else None,
        "month": int(rec.get("MONTH")) if rec.get("MONTH") else None,
        "day_of_week": (rec.get("DAY_OF_WEEK") or "").strip(),
        "hour": int(rec.get("HOUR")) if rec.get("HOUR") not in (None, "") else None,
        "street": _clean_street(rec.get("STREET")),
        "lat": lat,
        "lng": lng,
        "category": category,
        "bucket": CATEGORY_BUCKET[category],
    }


async def fetch_recent(limit: int = FETCH_LIMIT) -> list[dict[str, Any]]:
    """Pull the most recent `limit` incidents from BPD using CKAN SQL.

    The CKAN SQL endpoint lets us ORDER BY occurred date; the basic
    datastore_search returns rows in insertion order which is not what we
    want.
    """
    sql = (
        f'SELECT * FROM "{RESOURCE_ID}" '
        f'ORDER BY "OCCURRED_ON_DATE" DESC NULLS LAST '
        f'LIMIT {int(limit)}'
    )
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.get(CKAN_URL, params={"sql": sql})
        r.raise_for_status()
        data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"BPD CKAN responded with failure: {data}")
    return data["result"]["records"]


async def refresh_cache(db) -> dict[str, Any]:
    """Refresh the incidents collection. Idempotent — keyed on incident_number."""
    started = datetime.now(timezone.utc)
    logger.info("BPD refresh starting (limit=%s)", FETCH_LIMIT)
    raw = await fetch_recent()
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in raw:
        out = normalize(rec)
        if not out:
            continue
        key = out["incident_number"] or f"_{rec.get('_id')}"
        if key in seen:
            continue
        seen.add(key)
        out["incident_number"] = key
        normalized.append(out)

    if normalized:
        # Wipe and replace — these are the most recent rows by occurred date,
        # and BPD sometimes corrects old rows.
        await db.incidents.delete_many({})
        # Insert in chunks to keep BSON payloads reasonable.
        chunk = 1000
        for i in range(0, len(normalized), chunk):
            await db.incidents.insert_many(normalized[i:i + chunk])
        await db.incidents.create_index("occurred_ts")
        await db.incidents.create_index("category")
        await db.incidents.create_index("district")

    meta = {
        "_id": "bpd_cache",
        "last_refreshed": started.isoformat(),
        "record_count": len(normalized),
        "raw_count": len(raw),
    }
    await db.cache_meta.replace_one({"_id": "bpd_cache"}, meta, upsert=True)
    logger.info("BPD refresh complete: %s incidents", len(normalized))
    return meta


async def ensure_fresh(db) -> dict[str, Any]:
    """Refresh if cache is missing or older than CACHE_TTL."""
    meta = await db.cache_meta.find_one({"_id": "bpd_cache"})
    if meta:
        try:
            last = datetime.fromisoformat(meta["last_refreshed"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return meta
        except (KeyError, ValueError):
            pass
    try:
        return await refresh_cache(db)
    except Exception as exc:  # pragma: no cover - upstream flakiness
        logger.exception("BPD refresh failed: %s", exc)
        # Return whatever stale meta we have.
        return meta or {"_id": "bpd_cache", "record_count": 0, "error": str(exc)}


_refresh_lock = asyncio.Lock()


async def ensure_fresh_locked(db) -> dict[str, Any]:
    async with _refresh_lock:
        return await ensure_fresh(db)
