"""Supplemental official Boston Police datasets.

The main BPD crime-incident feed is the broad source for Boston Crime Map, but
it can lag. BPD also publishes current, narrower official datasets for Shots
Fired and Shootings. These rows do not include street-level coordinates, so we
map them at BPD district centroids and mark that clearly in the popup text.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from bpd_client import CATEGORY_BUCKET, DISTRICTS

logger = logging.getLogger(__name__)

CKAN_SQL_URL = "https://data.boston.gov/api/3/action/datastore_search_sql"
CACHE_TTL = timedelta(hours=1)
FETCH_LIMIT = 500

SHOTS_FIRED_RESOURCE_ID = "c1e4e6ac-8a84-4b48-8a23-7b2645a32ede"
SHOOTINGS_RESOURCE_ID = "73c7e069-701f-4910-986d-b950f46c91a1"

SHOTS_FIRED_SOURCE_URL = (
    "https://data.boston.gov/dataset/shots-fired/resource/"
    f"{SHOTS_FIRED_RESOURCE_ID}"
)
SHOOTINGS_SOURCE_URL = (
    "https://data.boston.gov/dataset/shootings/resource/"
    f"{SHOOTINGS_RESOURCE_ID}"
)

# Approximate BPD district centroids. These are intentionally coarse because
# the supplemental datasets expose district only, not addresses/coordinates.
DISTRICT_CENTROIDS: dict[str, tuple[float, float]] = {
    "A1": (42.3577, -71.0609),
    "A15": (42.3782, -71.0602),
    "A7": (42.3752, -71.0316),
    "B2": (42.3289, -71.0851),
    "B3": (42.2838, -71.0916),
    "C6": (42.3334, -71.0442),
    "C11": (42.3064, -71.0592),
    "D4": (42.3447, -71.0842),
    "D14": (42.3507, -71.1527),
    "E5": (42.2854, -71.1538),
    "E13": (42.3132, -71.1141),
    "E18": (42.2557, -71.1245),
}


def _parse_dt(raw: str | None) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    if raw.endswith("+00"):
        raw = raw + ":00"
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


async def _fetch(resource_id: str, date_field: str, limit: int = FETCH_LIMIT) -> list[dict[str, Any]]:
    sql = (
        f'SELECT * FROM "{resource_id}" '
        f'ORDER BY "{date_field}" DESC NULLS LAST '
        f'LIMIT {int(limit)}'
    )
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.get(CKAN_SQL_URL, params={"sql": sql})
        r.raise_for_status()
        data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"BPD supplemental CKAN failure: {data}")
    return data["result"]["records"]


def _normalize_shots_fired(rec: dict[str, Any]) -> Optional[dict[str, Any]]:
    district = (rec.get("district") or "UNK").strip().upper() or "UNK"
    coords = DISTRICT_CENTROIDS.get(district)
    occurred = _parse_dt(rec.get("incident_date"))
    if not coords or not occurred:
        return None
    incident = (rec.get("incident_num") or f"shots-fired-{rec.get('_id')}").strip()
    ballistic = str(rec.get("ballistics_evidence") or "").lower() == "t"
    district_label = DISTRICTS.get(district, district)
    evidence_note = "; ballistic evidence recovered" if ballistic else ""
    desc = f"Shots fired report — district-level location only ({district}: {district_label}{evidence_note})."
    return {
        "story_id": f"bpd-shots-fired-{incident}",
        "incident_number": f"bpd-shots-fired-{incident}",
        "headline": "Official BPD shots fired report",
        "title": "Official BPD shots fired report",
        "description": desc,
        "source_name": "Boston Police Department Shots Fired open data",
        "source_url": SHOTS_FIRED_SOURCE_URL,
        "source_index_url": SHOTS_FIRED_SOURCE_URL,
        "attribution": "Boston Police Department / Analyze Boston",
        "district": district,
        "shooting": True,
        "occurred_on": occurred.isoformat(),
        "occurred_ts": int(occurred.timestamp()),
        "day_of_week": occurred.strftime("%A"),
        "hour": occurred.hour,
        "street": f"District {district} centroid (approximate)",
        "lat": coords[0],
        "lng": coords[1],
        "category": "shooting",
        "bucket": CATEGORY_BUCKET["shooting"],
        "mappable": True,
        "location_precision": "district_centroid",
        "raw_source": "shots_fired",
        "raw": {k: rec.get(k) for k in ("_id", "incident_num", "incident_date", "district", "ballistics_evidence")},
    }


def _normalize_shooting(rec: dict[str, Any]) -> Optional[dict[str, Any]]:
    district = (rec.get("district") or "UNK").strip().upper() or "UNK"
    coords = DISTRICT_CENTROIDS.get(district)
    occurred = _parse_dt(rec.get("shooting_date"))
    if not coords or not occurred:
        return None
    incident = (rec.get("incident_num") or f"shooting-{rec.get('_id')}").strip()
    kind = (rec.get("shooting_type_v2") or "Shooting").strip() or "Shooting"
    multi = str(rec.get("multi_victim") or "").lower() == "t"
    district_label = DISTRICTS.get(district, district)
    multi_note = "; multi-victim incident" if multi else ""
    desc = f"Official BPD {kind.lower()} shooting — district-level location only ({district}: {district_label}{multi_note})."
    return {
        "story_id": f"bpd-shooting-{incident}",
        "incident_number": f"bpd-shooting-{incident}",
        "headline": f"Official BPD {kind.lower()} shooting report",
        "title": f"Official BPD {kind.lower()} shooting report",
        "description": desc,
        "source_name": "Boston Police Department Shootings open data",
        "source_url": SHOOTINGS_SOURCE_URL,
        "source_index_url": SHOOTINGS_SOURCE_URL,
        "attribution": "Boston Police Department / Analyze Boston",
        "district": district,
        "shooting": True,
        "occurred_on": occurred.isoformat(),
        "occurred_ts": int(occurred.timestamp()),
        "day_of_week": occurred.strftime("%A"),
        "hour": occurred.hour,
        "street": f"District {district} centroid (approximate)",
        "lat": coords[0],
        "lng": coords[1],
        "category": "shooting",
        "bucket": CATEGORY_BUCKET["shooting"],
        "mappable": True,
        "location_precision": "district_centroid",
        "raw_source": "shootings",
        "raw": {
            k: rec.get(k)
            for k in (
                "_id",
                "incident_num",
                "shooting_date",
                "district",
                "shooting_type_v2",
                "multi_victim",
            )
        },
    }


async def refresh_bpd_supplemental_cache(db) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    logger.info("BPD supplemental refresh starting")
    shots_raw, shootings_raw = await asyncio.gather(
        _fetch(SHOTS_FIRED_RESOURCE_ID, "incident_date"),
        _fetch(SHOOTINGS_RESOURCE_ID, "shooting_date"),
    )
    rows: list[dict[str, Any]] = []
    for rec in shots_raw:
        item = _normalize_shots_fired(rec)
        if item:
            rows.append(item)
    for rec in shootings_raw:
        item = _normalize_shooting(rec)
        if item:
            rows.append(item)

    # Dedupe exact incident/source collisions.
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique[row["incident_number"]] = row
    rows = sorted(unique.values(), key=lambda r: r.get("occurred_ts", 0), reverse=True)

    await db.bpd_supplemental.delete_many({})
    if rows:
        await db.bpd_supplemental.insert_many(rows)
        for field in ("occurred_ts", "category", "mappable", "district", "raw_source"):
            try:
                await db.bpd_supplemental.create_index(field)
            except Exception as exc:  # pragma: no cover - deployment-specific
                logger.warning("Skipping optional supplemental index %s: %s", field, exc)

    meta = {
        "_id": "bpd_supplemental_cache",
        "last_refreshed": started.isoformat(),
        "record_count": len(rows),
        "mappable_count": len(rows),
        "shots_fired_raw_count": len(shots_raw),
        "shootings_raw_count": len(shootings_raw),
        "sources": {
            "shots_fired": SHOTS_FIRED_SOURCE_URL,
            "shootings": SHOOTINGS_SOURCE_URL,
        },
        "location_precision": "district_centroid",
    }
    await db.cache_meta.replace_one({"_id": "bpd_supplemental_cache"}, meta, upsert=True)
    logger.info("BPD supplemental refresh complete: %s items", len(rows))
    return meta


async def ensure_bpd_supplemental_fresh(db) -> dict[str, Any]:
    meta = await db.cache_meta.find_one({"_id": "bpd_supplemental_cache"})
    if meta:
        try:
            last = datetime.fromisoformat(meta["last_refreshed"])
            if datetime.now(timezone.utc) - last < CACHE_TTL:
                return meta
        except (KeyError, ValueError):
            pass
    try:
        return await refresh_bpd_supplemental_cache(db)
    except Exception as exc:  # pragma: no cover - upstream flakiness
        logger.exception("BPD supplemental refresh failed: %s", exc)
        return meta or {"_id": "bpd_supplemental_cache", "record_count": 0, "error": str(exc)}


_refresh_lock = asyncio.Lock()


async def ensure_bpd_supplemental_fresh_locked(db) -> dict[str, Any]:
    async with _refresh_lock:
        return await ensure_bpd_supplemental_fresh(db)
