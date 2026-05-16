import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    fetchOverview,
    fetchRecent,
    fetchIncidents,
    fetchNeighborhoods,
    fetchCategories,
    fetchWickedPicks,
} from "@/lib/api";
import {
    CATEGORY_LABELS,
    colorFor,
    formatRelative,
} from "@/lib/format";
import CrimeMap from "@/components/CrimeMap";
import RotatingPlate from "@/components/RotatingPlate";
import { pinSvgInline } from "@/components/CrimePin";

const CITGO_IMG = null; // no longer used — RotatingPlate handles imagery

function Stat({ label, value, sub, testid }) {
    return (
        <div className="editorial-card p-4" data-testid={testid}>
            <div className="kicker">{label}</div>
            <div className="big-num text-5xl md:text-6xl mt-1">{value}</div>
            {sub && <div className="font-mono text-xs text-[var(--muted)] mt-1">{sub}</div>}
        </div>
    );
}

export default function HomePage() {
    const [overview, setOverview] = useState(null);
    const [recent, setRecent] = useState([]);
    const [mapIncidents, setMapIncidents] = useState([]);
    const [neighborhoods, setNeighborhoods] = useState([]);
    const [categories, setCategories] = useState([]);
    const [picks, setPicks] = useState([]);

    useEffect(() => {
        let alive = true;
        Promise.all([
            fetchOverview(),
            fetchRecent(8),
            fetchIncidents({ days: 30, limit: 1500 }),
            fetchNeighborhoods(),
            fetchCategories(),
            fetchWickedPicks(6),
        ]).then(([ov, rec, inc, ns, cats, p]) => {
            if (!alive) return;
            setOverview(ov);
            setRecent(rec.items || []);
            setMapIncidents(inc.items || []);
            setNeighborhoods(ns.items || []);
            setCategories(cats.items || []);
            setPicks(p.items || []);
        }).catch((e) => console.error("Home fetch failed", e));
        return () => { alive = false; };
    }, []);

    const c = overview?.counts || {};
    const wow = overview?.wow_change;

    return (
        <main className="max-w-7xl mx-auto px-5 pt-8 pb-10" data-testid="home-page">
            {/* HERO */}
            <section className="grid grid-cols-12 gap-6 paperdrop" data-testid="hero">
                <div className="col-span-12 lg:col-span-8">
                    <div className="kicker">Section A · Front Page</div>
                    <h2 className="headline-xl text-4xl sm:text-5xl md:text-7xl mt-2">
                        The map says it's fine.<br />
                        <em style={{ color: "var(--oxblood)" }}>Mostly.</em> Read the fine print.
                    </h2>
                    <p className="font-display italic text-lg sm:text-xl md:text-2xl text-[var(--muted)] mt-4 leading-snug max-w-2xl">
                        Twenty-three police districts, one harbor, four bridges, and a working theory that the back door is unlocked. Welcome.
                    </p>
                    <div className="mt-6 flex flex-wrap gap-3">
                        <Link to="/map" className="btn-ink" data-testid="hero-cta-map">Open the Crime Map →</Link>
                        <Link to="/wicked-picks" className="btn-ghost" data-testid="hero-cta-picks">This week's picks</Link>
                    </div>
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            const v = (e.target.elements.q.value || "").trim();
                            if (v) window.location.href = `/map?address=${encodeURIComponent(v)}`;
                        }}
                        className="mt-4 flex items-center border-2 border-[var(--ink)] bg-[var(--surface)] max-w-md"
                        data-testid="hero-address-form"
                    >
                        <input
                            name="q"
                            type="text"
                            placeholder="Look up an address — 700 Boylston, Fenway Park…"
                            className="flex-1 bg-transparent px-3 py-2.5 font-mono text-sm outline-none placeholder:text-[var(--muted)]"
                            data-testid="hero-address-input"
                        />
                        <button
                            type="submit"
                            className="bg-[var(--ink)] text-[var(--bg)] px-4 py-2.5 font-sub uppercase tracking-widest text-xs hover:bg-[var(--oxblood)]"
                            data-testid="hero-address-submit"
                        >
                            Look up →
                        </button>
                    </form>
                </div>
                <div className="col-span-12 lg:col-span-4">
                    <RotatingPlate height="h-72" testid="hero-plate" />
                </div>
            </section>

            {/* STATS BAR */}
            <section className="mt-12" data-testid="stats">
                <div className="rule mb-4" />
                <div className="kicker mb-3">By the numbers — reported incidents</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Stat
                        label="Last 24 hours"
                        value={c.day ?? "—"}
                        sub="Newly logged"
                        testid="stat-day"
                    />
                    <Stat
                        label="Last 7 days"
                        value={c.week ?? "—"}
                        sub={wow != null ? `${wow > 0 ? "+" : ""}${wow}% wk over wk` : "—"}
                        testid="stat-week"
                    />
                    <Stat
                        label="Last 30 days"
                        value={c.month ?? "—"}
                        sub="Citywide"
                        testid="stat-month"
                    />
                    <Stat
                        label="Last 12 months"
                        value={c.year?.toLocaleString?.() ?? c.year ?? "—"}
                        sub="In our window"
                        testid="stat-year"
                    />
                </div>
            </section>

            {/* MAP + RECENT BLOTTER */}
            <section className="mt-14 grid grid-cols-12 gap-6" data-testid="map-section">
                <div className="col-span-12 lg:col-span-8">
                    <div className="flex items-end justify-between mb-3 gap-3 flex-wrap">
                        <div>
                            <div className="kicker">Section B · The Map</div>
                            <h3 className="headline-lg text-4xl md:text-5xl mt-1">Where it happened, lately</h3>
                        </div>
                        <Link to="/map" className="btn-ghost text-xs" data-testid="map-section-open">Full map →</Link>
                    </div>
                    <CrimeMap incidents={mapIncidents} height="h-[55vh] min-h-[380px] md:h-[520px]" />
                </div>
                <aside className="col-span-12 lg:col-span-4" data-testid="blotter">
                    <div className="kicker">From the Blotter</div>
                    <h3 className="headline-lg text-3xl mt-1">Latest reports</h3>
                    <p className="font-display italic text-[var(--muted)] mt-1 text-sm">
                        Most recent incidents in the file.
                    </p>
                    <div className="mt-4 border-2 border-[var(--ink)] bg-[var(--surface)]">
                        <ul>
                            {recent.map((r, i) => (
                                <li
                                    key={r.incident_number}
                                    className={`p-3 ${i !== recent.length - 1 ? "border-b border-[var(--ink)]/30" : ""}`}
                                    data-testid={`blotter-row-${i}`}
                                >
                                    <div className="flex items-center gap-2">
                                        <span
                                            dangerouslySetInnerHTML={{ __html: pinSvgInline(r.category, 20) }}
                                            style={{ display: "inline-flex", alignItems: "center" }}
                                        />
                                        <span className="font-sub uppercase tracking-widest text-[10px]" style={{ color: colorFor(r.category) }}>
                                            {CATEGORY_LABELS[r.category]}
                                        </span>
                                        <span className="ml-auto font-mono text-[10px] text-[var(--muted)]">
                                            {formatRelative(r.occurred_on)}
                                        </span>
                                    </div>
                                    <div className="font-display text-lg leading-tight mt-1">{r.description}</div>
                                    <div className="font-mono text-[11px] text-[var(--muted)] mt-0.5">
                                        {r.street || "Boston"} · Dist. {r.district}
                                    </div>
                                </li>
                            ))}
                            {recent.length === 0 && (
                                <li className="p-4 font-mono text-sm text-[var(--muted)]">Loading the blotter…</li>
                            )}
                        </ul>
                    </div>
                </aside>
            </section>

            {/* WICKED PICKS */}
            <section className="mt-16" data-testid="wicked-picks-section">
                <div className="rule mb-4" />
                <div className="flex items-end justify-between mb-4 flex-wrap gap-3">
                    <div>
                        <div className="kicker">Section C · Editorial</div>
                        <h3 className="headline-xl text-4xl md:text-6xl mt-1">
                            Wicked Picks <span className="font-display italic text-[var(--muted)] text-3xl md:text-4xl">of the week</span>
                        </h3>
                    </div>
                    <Link to="/wicked-picks" className="btn-ink text-xs" data-testid="picks-all">All picks →</Link>
                </div>
                <div className="editorial-card-dark p-6 md:p-8 grid md:grid-cols-2 gap-6">
                    {picks.map((p, i) => (
                        <article
                            key={i}
                            className={`${i < 2 ? "border-b md:border-b md:border-r" : ""} ${i % 2 === 0 ? "md:border-r" : ""} md:pr-6 pb-6 ${i >= picks.length - 2 ? "md:border-b-0" : ""} border-neutral-700`}
                            data-testid={`pick-${i}`}
                        >
                            <div className="flex items-center gap-3 mb-2">
                                <span
                                    dangerouslySetInnerHTML={{ __html: pinSvgInline(p.category.key, 26) }}
                                    style={{ display: "inline-flex", alignItems: "center" }}
                                />
                                <span className="font-sub uppercase tracking-widest text-[10px] text-[var(--amber)]">
                                    {p.category.label}
                                </span>
                                <span className="font-mono text-[10px] text-neutral-400 ml-auto">{p.when}</span>
                            </div>
                            <h4 className="font-display text-2xl md:text-3xl leading-tight">{p.headline}</h4>
                            <p className="font-display italic text-lg text-neutral-300 mt-2 leading-snug">
                                "{p.commentary}"
                            </p>
                            <div className="mt-3 pt-3 border-t border-neutral-700 font-mono text-[11px] text-neutral-400 uppercase tracking-widest">
                                {p.incident.description} · {p.where}
                            </div>
                        </article>
                    ))}
                    {picks.length === 0 && (
                        <div className="font-mono text-neutral-400 col-span-2">Loading picks…</div>
                    )}
                </div>
            </section>

            {/* NEIGHBORHOODS GRID */}
            <section className="mt-16" data-testid="neighborhoods-section">
                <div className="rule mb-4" />
                <div className="flex items-end justify-between mb-4 flex-wrap gap-3">
                    <div>
                        <div className="kicker">Section D · The Map of Us</div>
                        <h3 className="headline-xl text-4xl md:text-6xl mt-1">Neighborhoods</h3>
                        <p className="font-display italic text-[var(--muted)] mt-1">
                            Nineteen places that all swear they're different. The numbers don't lie. The vibes do.
                        </p>
                    </div>
                    <Link to="/neighborhoods" className="btn-ghost text-xs" data-testid="neighborhoods-all">All neighborhoods →</Link>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {neighborhoods.slice(0, 9).map((n, i) => (
                        <Link
                            key={n.slug}
                            to={`/neighborhoods/${n.slug}`}
                            className="editorial-card p-5 block paperdrop"
                            style={{ animationDelay: `${i * 35}ms` }}
                            data-testid={`neighborhood-card-${n.slug}`}
                        >
                            <div className="flex items-baseline justify-between gap-3">
                                <h4 className="font-display text-2xl leading-tight">{n.name}</h4>
                                <span className="big-num text-3xl" style={{ color: "var(--oxblood)" }}>
                                    {n.incidents_30d}
                                </span>
                            </div>
                            <p className="font-display italic text-[var(--muted)] mt-1 leading-snug">
                                {n.tagline}
                            </p>
                            <p className="font-body text-sm mt-3 leading-relaxed">{n.blurb}</p>
                            <div className="rule-thin mt-4 pt-2 flex justify-between font-mono text-[10px] uppercase tracking-widest text-[var(--muted)]">
                                <span>Dist. {n.districts.join(" · ")}</span>
                                <span>30-day reports</span>
                            </div>
                        </Link>
                    ))}
                </div>
            </section>

            {/* CATEGORIES */}
            <section className="mt-16" data-testid="categories-section">
                <div className="rule mb-4" />
                <div className="kicker">Section E · Definitions</div>
                <h3 className="headline-xl text-4xl md:text-6xl mt-1">What counts as what</h3>
                <p className="font-display italic text-[var(--muted)] mt-1 max-w-2xl">
                    Police paperwork has rules. We translate. Click anything to dig in.
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-6">
                    {categories.map((cat) => (
                        <Link
                            key={cat.slug}
                            to={`/categories/${cat.slug}`}
                            className="editorial-card p-4 flex flex-col"
                            data-testid={`category-card-${cat.slug}`}
                        >
                            <span
                                dangerouslySetInnerHTML={{ __html: pinSvgInline(cat.key, 36) }}
                                style={{ display: "inline-flex", alignItems: "center", marginBottom: "0.5rem" }}
                            />
                            <div className="font-sub uppercase tracking-widest text-xs text-[var(--muted)]">
                                {cat.bucket}
                            </div>
                            <div className="font-display text-xl leading-tight mt-0.5">{cat.label}</div>
                            <div className="big-num text-3xl mt-2">{cat.incidents_30d}</div>
                            <div className="font-mono text-[10px] uppercase tracking-widest text-[var(--muted)] mt-0.5">
                                30-day reports
                            </div>
                        </Link>
                    ))}
                </div>
            </section>
        </main>
    );
}
