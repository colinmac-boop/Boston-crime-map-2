"""Boston Crime Map backend API tests.

Covers: health, incidents (list/filters/recent), stats, neighborhoods,
categories, wicked-picks, refresh, and the no-_id contract.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://api-production-d196.up.railway.app").rstrip("/")
API = f"{BASE_URL}/api"


def _contains_mongo_id(obj):
    """Recursively check if any '_id' key exists."""
    if isinstance(obj, dict):
        if "_id" in obj:
            return True
        return any(_contains_mongo_id(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_mongo_id(v) for v in obj)
    return False


# ---------- Health / meta ----------
class TestHealth:
    def test_health_ok(self):
        r = requests.get(f"{API}/health", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert isinstance(data["cached_incidents"], int)
        assert data["cached_incidents"] > 0, "Expected cached incidents > 0"


# ---------- Incidents ----------
class TestIncidents:
    def test_recent_default_limit(self):
        r = requests.get(f"{API}/incidents/recent?limit=8", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) == 8
        required = {"incident_number", "lat", "lng", "category", "description", "district", "occurred_on"}
        for item in data["items"]:
            assert required.issubset(item.keys()), f"Missing fields: {required - set(item.keys())}"
        assert not _contains_mongo_id(data), "MongoDB _id leaked in /incidents/recent"

    def test_incidents_filter_category(self):
        r = requests.get(f"{API}/incidents?category=larceny&limit=50", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        for it in data["items"]:
            assert it["category"] == "larceny"

    def test_incidents_filter_neighborhood(self):
        r = requests.get(f"{API}/incidents?neighborhood=dorchester&limit=50", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        # Dorchester districts: C11, B3
        for it in data["items"]:
            assert it["district"] in {"C11", "B3"}

    def test_incidents_filter_district(self):
        r = requests.get(f"{API}/incidents?district=C11&limit=20", timeout=30)
        assert r.status_code == 200
        data = r.json()
        for it in data["items"]:
            assert it["district"] == "C11"

    def test_incidents_filter_days(self):
        r = requests.get(f"{API}/incidents?days=7", timeout=30)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_incidents_invalid_category_404(self):
        r = requests.get(f"{API}/incidents?category=not-a-category", timeout=30)
        assert r.status_code == 404

    def test_incidents_invalid_neighborhood_404(self):
        r = requests.get(f"{API}/incidents?neighborhood=mordor", timeout=30)
        assert r.status_code == 404


# ---------- Stats ----------
class TestStats:
    def test_overview(self):
        r = requests.get(f"{API}/stats/overview", timeout=30)
        assert r.status_code == 200
        data = r.json()
        counts = data["counts"]
        for key in ("day", "week", "month", "year"):
            assert key in counts
            assert isinstance(counts[key], int)
            assert counts[key] >= 0
        assert isinstance(data["top_categories"], list)
        assert len(data["top_categories"]) > 0
        for c in data["top_categories"]:
            for k in ("key", "label", "count", "slug"):
                assert k in c
        assert isinstance(data["top_districts"], list)
        assert not _contains_mongo_id({k: v for k, v in data.items() if k != "cache"}), "MongoDB _id leaked in stats"


# ---------- Neighborhoods ----------
class TestNeighborhoods:
    def test_list(self):
        r = requests.get(f"{API}/neighborhoods", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 19, f"Expected 19 neighborhoods, got {data['count']}"
        assert len(data["items"]) == 19
        for n in data["items"]:
            for k in ("slug", "name", "districts", "tagline", "blurb", "incidents_30d"):
                assert k in n, f"Missing {k} in neighborhood"

    def test_detail_south_boston(self):
        r = requests.get(f"{API}/neighborhoods/south-boston", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "south-boston"
        assert data["name"] == "South Boston"
        stats = data["stats"]
        assert "breakdown" in stats
        assert "incidents_30d" in stats
        assert "incidents_7d" in stats
        assert isinstance(data["recent"], list)
        assert not _contains_mongo_id(data), "MongoDB _id leaked"

    def test_detail_not_found(self):
        r = requests.get(f"{API}/neighborhoods/not-real", timeout=30)
        assert r.status_code == 404


# ---------- Categories ----------
class TestCategories:
    def test_list(self):
        r = requests.get(f"{API}/categories", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 10
        assert len(data["items"]) == 10
        for c in data["items"]:
            for k in ("slug", "key", "label", "bucket", "definition", "boston_note", "incidents_30d"):
                assert k in c

    def test_detail_larceny(self):
        r = requests.get(f"{API}/categories/larceny", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "larceny"
        assert data["key"] == "larceny"
        assert "by_district" in data["stats"]
        assert isinstance(data["recent"], list)
        assert not _contains_mongo_id(data), "MongoDB _id leaked"

    def test_detail_not_found(self):
        r = requests.get(f"{API}/categories/not-real", timeout=30)
        assert r.status_code == 404


# ---------- Wicked Picks ----------
class TestWickedPicks:
    def test_picks(self):
        r = requests.get(f"{API}/wicked-picks", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) > 0, "Wicked picks items should not be empty (uses 30d window)"
        for pick in data["items"]:
            for k in ("headline", "commentary", "incident", "category", "when", "where"):
                assert k in pick, f"Pick missing {k}"
        assert not _contains_mongo_id(data), "MongoDB _id leaked"


# ---------- Refresh ----------
class TestRefresh:
    def test_refresh(self):
        r = requests.post(f"{API}/refresh", timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert data.get("record_count", 0) > 0
