import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchIncidents, fetchNeighborhoods, fetchCategories, fetchStories, fetchBpdSupplemental } from "@/lib/api";
import { CATEGORY_LABELS, CATEGORY_ORDER, colorFor } from "@/lib/format";
import CrimeMap from "@/components/CrimeMap";
import { pinSvgInline } from "@/components/CrimePin";
import AddressSearch from "@/components/AddressSearch";

const DAYS_OPTIONS = [
    { v: 7, l: "7d" },
    { v: 30, l: "30d" },
    { v: 90, l: "90d" },
    { v: 180, l: "6mo" },
    { v: 365, l: "1yr" },
];

export default function MapPage() {
    const [params, setParams] = useSearchParams();
    const initialCat = params.get("category") || "";
    const initialN = params.get("neighborhood") || "";
    const initialD = parseInt(params.get("days") || "90", 10);

    const [days, setDays] = useState(initialD);
    const [category, setCategory] = useState(initialCat);
    const [neighborhood, setNeighborhood] = useState(initialN);
    const [incidents, setIncidents] = useState([]);
    const [stories, setStories] = useState([]);
    const [neighborhoods, setNeighborhoods] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState(null); // { hit, near, radius }
    const initialAddress = params.get("address") || "";

    useEffect(() => {
        fetchNeighborhoods().then((r) => setNeighborhoods(r.items || []));
        fetchCategories().then((r) => setCategories(r.items || []));
    }, []);

    useEffect(() => {
        const nextCat = params.get("category") || "";
        const nextNeighborhood = params.get("neighborhood") || "";
        const parsedDays = parseInt(params.get("days") || "90", 10);
        const nextDays = Number.isFinite(parsedDays) ? parsedDays : 90;
        if (nextCat !== category) setCategory(nextCat);
        if (nextNeighborhood !== neighborhood) setNeighborhood(nextNeighborhood);
        if (nextDays !== days) setDays(nextDays);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [params]);

    useEffect(() => {
        setLoading(true);
        const q = { days, limit: 2000 };
        if (category) q.category = category;
        if (neighborhood) q.neighborhood = neighborhood;
        const storyQ = { days };
        if (category) storyQ.category = category;
        if (neighborhood) storyQ.neighborhood = neighborhood;
        Promise.allSettled([
            fetchIncidents(q),
            fetchStories(200, true, storyQ),
            fetchBpdSupplemental(500, storyQ),
        ])
            .then(([incidentResult, storyResult, supplementalResult]) => {
                if (incidentResult.status === "fulfilled") {
                    setIncidents(incidentResult.value.items || []);
                } else {
                    console.error("Incident fetch failed", incidentResult.reason);
                    setIncidents([]);
                }
                const nextStories = [];
                if (storyResult.status === "fulfilled") {
                    nextStories.push(...(storyResult.value.items || []));
                } else {
                    console.error("Story fetch failed", storyResult.reason);
                }
                if (supplementalResult.status === "fulfilled") {
                    nextStories.push(...(supplementalResult.value.items || []));
                } else {
                    console.error("BPD supplemental fetch failed", supplementalResult.reason);
                }
                const seen = new Set();
                setStories(nextStories
                    .sort((a, b) => (b.occurred_ts || 0) - (a.occurred_ts || 0))
                    .filter((item) => {
                        const key = item.incident_number || item.story_id || item.source_url;
                        if (!key) return true;
                        if (seen.has(key)) return false;
                        seen.add(key);
                        return true;
                    }));
            })
            .finally(() => setLoading(false));

        // Sync URL
        const np = {};
        if (category) np.category = category;
        if (neighborhood) np.neighborhood = neighborhood;
        if (days !== 90) np.days = String(days);
        setParams(np, { replace: true });
    }, [days, category, neighborhood, setParams]);

    const counts = useMemo(() => {
        const c = { total: incidents.length };
        incidents.forEach((i) => { c[i.category] = (c[i.category] || 0) + 1; });
        return c;
    }, [incidents]);

    // When the address search returns results, swap the map's incident set
    // to the nearby items so the focus is tight on the address.
    const mapIncidents = search ? search.near.items : [...stories, ...incidents];
    const mapKey = search
        ? `search-${search.hit.lat}-${search.hit.lng}-${search.near.count}`
        : `filters-${category || "all"}-${neighborhood || "all"}-${days}-${incidents.length}-${stories.length}`;
    const searchPin = search
        ? { lat: search.hit.lat, lng: search.hit.lng, label: search.hit.label }
        : null;

    return (
        <main className="max-w-7xl mx-auto px-5 pt-8 pb-10" data-testid="map-page">
            <div className="kicker">Section · Interactive Map</div>
            <h2 className="headline-xl text-4xl md:text-6xl mt-1">The full picture</h2>
            <p className="font-display italic text-[var(--muted)] mt-2 max-w-2xl">
                Filter by category, by neighborhood, by how far back you want to look. Map updates instantly. Markers cluster until you zoom in.
            </p>

            {/* Address search */}
            <div className="mt-6">
                <AddressSearch
                    onResult={(r) => setSearch(r)}
                    onClear={() => setSearch(null)}
                    days={Math.max(days, 90)}
                    category={category}
                    initialQuery={initialAddress}
                />
            </div>

            {/* Filter bar */}
            <div className="mt-4 border-2 border-[var(--ink)] bg-[var(--surface)] p-4 grid md:grid-cols-3 gap-4" data-testid="map-filters">
                <div>
                    <div className="kicker mb-1.5">Time window</div>
                    <div className="flex flex-wrap gap-1.5">
                        {DAYS_OPTIONS.map((o) => (
                            <button
                                key={o.v}
                                onClick={() => setDays(o.v)}
                                data-testid={`filter-days-${o.v}`}
                                className={`px-3 py-1.5 font-sub uppercase tracking-widest text-xs border-2 border-[var(--ink)] ${
                                    days === o.v
                                        ? "bg-[var(--ink)] text-[var(--bg)]"
                                        : "bg-[var(--bg)] hover:bg-[var(--ink)] hover:text-[var(--bg)]"
                                }`}
                            >
                                {o.l}
                            </button>
                        ))}
                    </div>
                </div>
                <div>
                    <div className="kicker mb-1.5">Category</div>
                    <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="w-full border-2 border-[var(--ink)] bg-[var(--bg)] px-3 py-2 font-mono text-sm"
                        data-testid="filter-category"
                    >
                        <option value="">All categories</option>
                        {CATEGORY_ORDER.map((k) => {
                            const slug = categories.find((c) => c.key === k)?.slug || k;
                            return (
                                <option key={k} value={slug}>{CATEGORY_LABELS[k]}</option>
                            );
                        })}
                    </select>
                </div>
                <div>
                    <div className="kicker mb-1.5">Neighborhood</div>
                    <select
                        value={neighborhood}
                        onChange={(e) => setNeighborhood(e.target.value)}
                        className="w-full border-2 border-[var(--ink)] bg-[var(--bg)] px-3 py-2 font-mono text-sm"
                        data-testid="filter-neighborhood"
                    >
                        <option value="">All neighborhoods</option>
                        {neighborhoods.map((n) => (
                            <option key={n.slug} value={n.slug}>{n.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Status row */}
            <div className="mt-4 flex items-center justify-between font-mono text-xs text-[var(--muted)] uppercase tracking-widest" data-testid="map-status">
                <span>
                    {search
                        ? <>Showing <strong className="text-[var(--ink)]">{search.near.count}</strong> incidents within {search.radius} mi of your search</>
                        : <>Showing <strong className="text-[var(--ink)]">{counts.total.toLocaleString()}</strong> incidents + <strong className="text-[var(--ink)]">{stories.length}</strong> attributed story pins · {days}-day window</>
                    }
                </span>
                {loading && <span className="animate-pulse">Loading…</span>}
                {(category || neighborhood) && !search && (
                    <button
                        onClick={() => { setCategory(""); setNeighborhood(""); }}
                        className="underline hover:text-[var(--oxblood)]"
                        data-testid="map-clear"
                    >
                        Clear filters ×
                    </button>
                )}
            </div>

            <div className="mt-3">
                <CrimeMap
                    key={mapKey}
                    incidents={mapIncidents}
                    height="h-[60vh] min-h-[420px] md:h-[640px]"
                    searchPin={searchPin}
                    searchRadiusMi={search?.radius || null}
                    autoFit={!search && Boolean(category || neighborhood)}
                />
            </div>

            {/* Quick category chips */}
            <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-2" data-testid="quick-categories">
                {CATEGORY_ORDER.map((k) => {
                    const slug = categories.find((c) => c.key === k)?.slug || k;
                    return (
                        <Link
                            key={k}
                            to={`/categories/${slug}`}
                            className="editorial-card p-3 flex items-center gap-2 text-sm"
                        >
                            <span dangerouslySetInnerHTML={{ __html: pinSvgInline(k, 22) }} style={{ display: "inline-flex" }} />
                            <span className="font-sub uppercase tracking-widest text-[11px]">{CATEGORY_LABELS[k]}</span>
                            <span className="ml-auto font-mono text-xs text-[var(--muted)]">{counts[k] || 0}</span>
                        </Link>
                    );
                })}
            </div>
        </main>
    );
}
