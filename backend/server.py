"""Boston Crime Map — FastAPI server.

Endpoints all live under /api. Crime data comes from BPD's CKAN open data,
cached in MongoDB with a 1-hour TTL. Editorial bits (neighborhoods, category
copy, wicked-picks) are generated server-side so the frontend can stay simple.
"""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from bpd_client import DISTRICTS, ensure_fresh_locked, refresh_cache
from boston_data import (
    CATEGORIES,
    CATEGORY_BY_KEY,
    CATEGORY_BY_SLUG,
    NEIGHBORHOODS,
    NEIGHBORHOOD_BY_SLUG,
)
from geocode import geocode, haversine_miles

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Boston Crime Map API")
api = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECTION = {"_id": 0}


async def _bootstrap_if_empty() -> None:
    """On first request, make sure we have some data to serve."""
    meta = await db.cache_meta.find_one({"_id": "bpd_cache"})
    count = await db.incidents.estimated_document_count()
    if not meta or count == 0:
        await ensure_fresh_locked(db)
    else:
        # Fire-and-forget freshness check (returns quickly if still fresh).
        await ensure_fresh_locked(db)


def _since_ts(days: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Incident(BaseModel):
    incident_number: str
    description: str
    district: str
    shooting: bool
    occurred_on: Optional[str] = None
    occurred_ts: int = 0
    day_of_week: str = ""
    hour: Optional[int] = None
    street: str = ""
    lat: float
    lng: float
    category: str
    bucket: str


# ---------------------------------------------------------------------------
# Routes — meta / health
# ---------------------------------------------------------------------------


@api.get("/images/plates")
async def image_plates() -> dict[str, Any]:
    """Return self-hosted Boston imagery for rotating editorial plates."""
    return {
        "items": [
            {
                "slug": "fenway",
                "src": "/api/static/images/fenway-scoreboard.jpg",
                "caption": "Above: Fenway. The sign still watches the city.",
                "where": "Kenmore Square",
            },
            {
                "slug": "beacon-hill",
                "src": "/api/static/images/brownstones.jpg",
                "caption": "Above: A street that was old before your great-grandfather got here.",
                "where": "Beacon Hill",
            },
            {
                "slug": "zakim",
                "src": "/api/static/images/zakim-night.jpg",
                "caption": "Above: The Zakim. The big-shouldered cousin of the Tobin.",
                "where": "Charlestown Bridge",
            },
            {
                "slug": "harbor",
                "src": "/api/static/images/boston-skyline-bay.jpg",
                "caption": "Above: The harbor. The reason any of this is here at all.",
                "where": "Boston Harbor",
            },
        ]
    }


@api.get("/geocode")
async def geocode_address(q: str = Query(..., min_length=2, max_length=200)) -> dict[str, Any]:
    """Geocode a free-form address using OSM Nominatim, biased to Boston."""
    hit = await geocode(db, q)
    if not hit:
        raise HTTPException(404, "No Boston-area match for that address.")
    return hit


@api.get("/incidents/near")
async def incidents_near(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_mi: float = Query(0.5, ge=0.05, le=5.0),
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(500, ge=1, le=2000),
) -> dict[str, Any]:
    """Incidents within `radius_mi` of (lat, lng) over the last `days`."""
    await _bootstrap_if_empty()

    # Bounding-box pre-filter (degree-approx) to avoid Haversine on all 8k rows.
    # 1 mile ≈ 0.0145° lat, ~0.0195° lng at Boston's latitude.
    dlat = radius_mi / 69.0
    dlng = radius_mi / 53.0
    box_filter = {
        "occurred_ts": {"$gte": _since_ts(days)},
        "lat": {"$gte": lat - dlat, "$lte": lat + dlat},
        "lng": {"$gte": lng - dlng, "$lte": lng + dlng},
    }
    candidates = await db.incidents.find(box_filter, PROJECTION).to_list(length=5000)

    rows: list[dict[str, Any]] = []
    for c in candidates:
        d = haversine_miles(lat, lng, c["lat"], c["lng"])
        if d <= radius_mi:
            c["distance_mi"] = round(d, 3)
            rows.append(c)
    rows.sort(key=lambda r: r["distance_mi"])
    rows = rows[:limit]

    breakdown: dict[str, int] = {}
    for r in rows:
        breakdown[r["category"]] = breakdown.get(r["category"], 0) + 1
    breakdown_rows = [
        {
            "key": k,
            "label": CATEGORY_BY_KEY.get(k, {}).get("label", k),
            "slug": CATEGORY_BY_KEY.get(k, {}).get("slug", k),
            "count": v,
        }
        for k, v in sorted(breakdown.items(), key=lambda x: -x[1])
    ]

    return {
        "center": {"lat": lat, "lng": lng},
        "radius_mi": radius_mi,
        "days": days,
        "count": len(rows),
        "items": rows,
        "breakdown": breakdown_rows,
    }


@api.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "Boston Crime Map API",
        "source": "Boston Police Department open data (data.boston.gov)",
        "voice": "wicked dry",
    }


@api.get("/health")
async def health() -> dict[str, Any]:
    meta = await db.cache_meta.find_one({"_id": "bpd_cache"}, PROJECTION)
    count = await db.incidents.estimated_document_count()
    return {
        "status": "ok",
        "cached_incidents": count,
        "cache": meta,
    }


@api.post("/refresh")
async def refresh() -> dict[str, Any]:
    """Force a re-fetch from BPD. Useful after deploys."""
    meta = await refresh_cache(db)
    return meta


# ---------------------------------------------------------------------------
# Routes — incidents
# ---------------------------------------------------------------------------


@api.get("/incidents")
async def list_incidents(
    category: Optional[str] = Query(None, description="Category slug or key."),
    district: Optional[str] = Query(None, description="BPD district code, e.g. A1."),
    neighborhood: Optional[str] = Query(None, description="Neighborhood slug."),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(500, ge=1, le=2000),
) -> dict[str, Any]:
    await _bootstrap_if_empty()

    query: dict[str, Any] = {"occurred_ts": {"$gte": _since_ts(days)}}

    if category:
        # accept slug or key
        cat = CATEGORY_BY_SLUG.get(category) or CATEGORY_BY_KEY.get(category)
        if not cat:
            raise HTTPException(404, f"Unknown category: {category}")
        query["category"] = cat["key"]

    if neighborhood:
        n = NEIGHBORHOOD_BY_SLUG.get(neighborhood)
        if not n:
            raise HTTPException(404, f"Unknown neighborhood: {neighborhood}")
        query["district"] = {"$in": n["districts"]}
    elif district:
        query["district"] = district.upper()

    cursor = db.incidents.find(query, PROJECTION).sort("occurred_ts", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"count": len(items), "items": items}


@api.get("/incidents/recent")
async def recent_incidents(limit: int = Query(12, ge=1, le=50)) -> dict[str, Any]:
    await _bootstrap_if_empty()
    cursor = db.incidents.find({}, PROJECTION).sort("occurred_ts", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"count": len(items), "items": items}


# ---------------------------------------------------------------------------
# Routes — stats
# ---------------------------------------------------------------------------


@api.get("/stats/overview")
async def stats_overview() -> dict[str, Any]:
    await _bootstrap_if_empty()

    now = datetime.now(timezone.utc)
    windows = {
        "day": int((now - timedelta(days=1)).timestamp()),
        "week": int((now - timedelta(days=7)).timestamp()),
        "month": int((now - timedelta(days=30)).timestamp()),
        "year": int((now - timedelta(days=365)).timestamp()),
    }

    counts: dict[str, int] = {}
    for key, ts in windows.items():
        counts[key] = await db.incidents.count_documents({"occurred_ts": {"$gte": ts}})

    # WoW % change for the week window
    prev_week_start = int((now - timedelta(days=14)).timestamp())
    prev_week_end = windows["week"]
    prev_week = await db.incidents.count_documents(
        {"occurred_ts": {"$gte": prev_week_start, "$lt": prev_week_end}}
    )
    wow_change = None
    if prev_week > 0:
        wow_change = round((counts["week"] - prev_week) / prev_week * 100, 1)

    # Top categories in the last 30 days
    pipeline = [
        {"$match": {"occurred_ts": {"$gte": windows["month"]}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cats = await db.incidents.aggregate(pipeline).to_list(length=20)
    top_categories = [
        {
            "key": c["_id"],
            "label": CATEGORY_BY_KEY.get(c["_id"], {}).get("label", c["_id"].title()),
            "count": c["count"],
            "slug": CATEGORY_BY_KEY.get(c["_id"], {}).get("slug", c["_id"]),
        }
        for c in cats
    ]

    # Top districts in the last 30 days
    pipeline_d = [
        {"$match": {"occurred_ts": {"$gte": windows["month"]}}},
        {"$group": {"_id": "$district", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 12},
    ]
    dists = await db.incidents.aggregate(pipeline_d).to_list(length=12)
    top_districts = [
        {"district": d["_id"], "label": DISTRICTS.get(d["_id"], d["_id"]), "count": d["count"]}
        for d in dists
    ]

    meta = await db.cache_meta.find_one({"_id": "bpd_cache"}, PROJECTION)

    return {
        "counts": counts,
        "wow_change": wow_change,
        "top_categories": top_categories,
        "top_districts": top_districts,
        "cache": meta,
    }


# ---------------------------------------------------------------------------
# Routes — neighborhoods
# ---------------------------------------------------------------------------


@api.get("/neighborhoods")
async def list_neighborhoods() -> dict[str, Any]:
    await _bootstrap_if_empty()
    since = _since_ts(30)
    out: list[dict[str, Any]] = []
    for n in NEIGHBORHOODS:
        count = await db.incidents.count_documents(
            {"district": {"$in": n["districts"]}, "occurred_ts": {"$gte": since}}
        )
        out.append({**n, "incidents_30d": count})
    out.sort(key=lambda x: x["name"])
    return {"count": len(out), "items": out}


@api.get("/neighborhoods/{slug}")
async def neighborhood_detail(slug: str) -> dict[str, Any]:
    await _bootstrap_if_empty()
    n = NEIGHBORHOOD_BY_SLUG.get(slug)
    if not n:
        raise HTTPException(404, "Neighborhood not found")

    base = {"district": {"$in": n["districts"]}}
    since_30 = _since_ts(30)
    since_7 = _since_ts(7)

    count_30 = await db.incidents.count_documents({**base, "occurred_ts": {"$gte": since_30}})
    count_7 = await db.incidents.count_documents({**base, "occurred_ts": {"$gte": since_7}})

    # Category breakdown last 30d
    cats = await db.incidents.aggregate([
        {"$match": {**base, "occurred_ts": {"$gte": since_30}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(length=20)
    breakdown = [
        {
            "key": c["_id"],
            "label": CATEGORY_BY_KEY.get(c["_id"], {}).get("label", c["_id"]),
            "slug": CATEGORY_BY_KEY.get(c["_id"], {}).get("slug", c["_id"]),
            "count": c["count"],
        }
        for c in cats
    ]

    recent = await db.incidents.find({**base}, PROJECTION).sort("occurred_ts", -1).limit(25).to_list(25)

    return {
        **n,
        "stats": {
            "incidents_30d": count_30,
            "incidents_7d": count_7,
            "breakdown": breakdown,
        },
        "recent": recent,
    }


# ---------------------------------------------------------------------------
# Routes — categories
# ---------------------------------------------------------------------------


@api.get("/categories")
async def list_categories() -> dict[str, Any]:
    await _bootstrap_if_empty()
    since = _since_ts(30)
    counts = await db.incidents.aggregate([
        {"$match": {"occurred_ts": {"$gte": since}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    ]).to_list(length=50)
    count_map = {c["_id"]: c["count"] for c in counts}
    items = [{**c, "incidents_30d": count_map.get(c["key"], 0)} for c in CATEGORIES]
    return {"count": len(items), "items": items}


@api.get("/categories/{slug}")
async def category_detail(slug: str) -> dict[str, Any]:
    await _bootstrap_if_empty()
    cat = CATEGORY_BY_SLUG.get(slug)
    if not cat:
        raise HTTPException(404, "Category not found")
    since_30 = _since_ts(30)
    since_7 = _since_ts(7)

    base = {"category": cat["key"]}
    count_30 = await db.incidents.count_documents({**base, "occurred_ts": {"$gte": since_30}})
    count_7 = await db.incidents.count_documents({**base, "occurred_ts": {"$gte": since_7}})

    by_district = await db.incidents.aggregate([
        {"$match": {**base, "occurred_ts": {"$gte": since_30}}},
        {"$group": {"_id": "$district", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(length=20)
    dist_rows = [
        {"district": d["_id"], "label": DISTRICTS.get(d["_id"], d["_id"]), "count": d["count"]}
        for d in by_district
    ]

    recent = await db.incidents.find(base, PROJECTION).sort("occurred_ts", -1).limit(25).to_list(25)

    return {
        **cat,
        "stats": {"incidents_30d": count_30, "incidents_7d": count_7, "by_district": dist_rows},
        "recent": recent,
    }


# ---------------------------------------------------------------------------
# Wicked Picks — editorial picks with dry Boston commentary
# ---------------------------------------------------------------------------

COMMENTARY_TEMPLATES = {
    "larceny": [
        "Package theft. Of course. Pull your Amazon orders in before 5, hon.",
        "Bike's gone. The U-lock isn't a suggestion.",
        "Someone got their phone lifted on the sidewalk. Two-handed grip, people.",
        "Catalytic converter logged again. The hybrid you bought to save the planet did not save itself.",
    ],
    "vehicle_theft": [
        "Another Hyundai or Kia. We do not need to keep doing this.",
        "Car was running. In Boston. With the keys in it. We will not be commenting further.",
        "Reported stolen from a side street. Recovered three blocks over by Wednesday, probably.",
    ],
    "burglary": [
        "Back door was unlocked. It's 2026. Lock the back door.",
        "Side entry of a triple-decker. Classic.",
        "Storefront overnight. The alarm panel was decorative, apparently.",
    ],
    "assault": [
        "Disagreement that escalated. Bystander called it in.",
        "Bar incident. We will let the lawyers fight it out.",
        "Domestic call. Officers separated the parties. The neighbors heard everything.",
    ],
    "robbery": [
        "Phone, wallet, gone. Outside a transit stop, naturally.",
        "Two suspects fled on foot. The descriptions are vague because they always are.",
    ],
    "shooting": [
        "Shots fired call. Police are investigating. We are not making jokes about this one.",
        "Confirmed shooting. Detectives are on it. No further snark — it isn't earned.",
    ],
    "vandalism": [
        "Graffiti. The artist has range but not consent.",
        "Broken window. The brick remains at large.",
    ],
    "drugs": [
        "Drug arrest logged. Enforcement priorities, etc.",
        "Possession charge. The paperwork is the actual punishment.",
    ],
    "homicide": [
        "A life was lost. BPD homicide is on it. That is all we will write here.",
    ],
    "other": [
        "Disturbance call. Could be anything from a noise complaint to a family reunion.",
        "Officers responded. The report says 'investigated' and that is the report.",
    ],
}

PICK_HEADLINES = {
    "larceny": "Theft of the Week",
    "vehicle_theft": "Car Disappeared Again",
    "burglary": "Door Was Not Locked",
    "assault": "Words Stopped Working",
    "robbery": "On-Foot Departure",
    "shooting": "Shots Fired Report",
    "vandalism": "Spray Paint Studies",
    "drugs": "Possession Filed",
    "homicide": "Logged With Detectives",
    "other": "Call For Service",
}


def _format_when(occurred: Optional[str]) -> str:
    if not occurred:
        return "Recently"
    try:
        dt = datetime.fromisoformat(occurred)
    except ValueError:
        return "Recently"
    now = datetime.now(timezone.utc)
    delta = now - dt
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "Within the hour"
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days}d ago"
    return dt.strftime("%b %-d")


@api.get("/wicked-picks")
async def wicked_picks(limit: int = Query(6, ge=1, le=12)) -> dict[str, Any]:
    """Editorially-flavored picks: pull a recent incident from a few different
    categories, deterministic per day so the same day shows the same picks."""
    await _bootstrap_if_empty()

    # BPD's dataset can lag a couple of weeks behind realtime, so we draw from
    # the last 30 days of available data, not the last 7.
    since = _since_ts(30)
    # Deterministic seed per UTC date so reloads don't reshuffle constantly.
    seed = datetime.now(timezone.utc).strftime("%Y%m%d")
    rng = random.Random(seed)

    desired_order = [
        "shooting",
        "homicide",
        "robbery",
        "assault",
        "burglary",
        "vehicle_theft",
        "larceny",
        "vandalism",
        "drugs",
        "other",
    ]

    picks: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for cat in desired_order:
        if len(picks) >= limit:
            break
        candidates = await db.incidents.find(
            {"category": cat, "occurred_ts": {"$gte": since}}, PROJECTION
        ).sort("occurred_ts", -1).limit(25).to_list(25)
        if not candidates:
            continue
        choice = rng.choice(candidates)
        if choice["incident_number"] in used_ids:
            continue
        used_ids.add(choice["incident_number"])

        templates = COMMENTARY_TEMPLATES.get(cat, COMMENTARY_TEMPLATES["other"])
        commentary = rng.choice(templates)
        cat_meta = CATEGORY_BY_KEY.get(cat, {})

        picks.append({
            "headline": PICK_HEADLINES.get(cat, "From the Blotter"),
            "commentary": commentary,
            "incident": choice,
            "category": {
                "key": cat,
                "slug": cat_meta.get("slug", cat),
                "label": cat_meta.get("label", cat.title()),
                "bucket": cat_meta.get("bucket", "other"),
            },
            "when": _format_when(choice.get("occurred_on")),
            "where": _humanize_where(choice),
        })

    return {"count": len(picks), "items": picks, "as_of": datetime.now(timezone.utc).isoformat()}


def _humanize_where(inc: dict[str, Any]) -> str:
    parts: list[str] = []
    street = inc.get("street") or ""
    if street:
        parts.append(street)
    d = inc.get("district")
    if d and d in DISTRICTS:
        parts.append(DISTRICTS[d].split(" / ")[0])
    return " · ".join(parts) or "Boston"


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

app.include_router(api)

# Serve self-hosted Boston imagery under /api/static so it routes through the
# Kubernetes ingress (any /api path goes to the backend).
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.is_dir():
    app.mount("/api/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    # Kick off a refresh in the background; don't block startup.
    import asyncio
    asyncio.create_task(_bootstrap_if_empty())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    client.close()
