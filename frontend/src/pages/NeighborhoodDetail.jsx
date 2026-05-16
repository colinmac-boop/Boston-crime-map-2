import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchNeighborhood, fetchIncidents } from "@/lib/api";
import { CATEGORY_LABELS, colorFor, formatRelative } from "@/lib/format";
import CrimeMap from "@/components/CrimeMap";
import { pinSvgInline } from "@/components/CrimePin";

export default function NeighborhoodDetail() {
    const { slug } = useParams();
    const [n, setN] = useState(null);
    const [incidents, setIncidents] = useState([]);
    const [notFound, setNotFound] = useState(false);

    useEffect(() => {
        setN(null);
        setIncidents([]);
        setNotFound(false);
        fetchNeighborhood(slug)
            .then((data) => setN(data))
            .catch(() => setNotFound(true));
        fetchIncidents({ neighborhood: slug, days: 30, limit: 1500 })
            .then((r) => setIncidents(r.items || []))
            .catch(() => {});
    }, [slug]);

    const mapCenter = useMemo(() => {
        if (incidents.length === 0) return [42.34, -71.09];
        const lats = incidents.map((i) => i.lat);
        const lngs = incidents.map((i) => i.lng);
        return [
            lats.reduce((a, b) => a + b, 0) / lats.length,
            lngs.reduce((a, b) => a + b, 0) / lngs.length,
        ];
    }, [incidents]);

    if (notFound) {
        return (
            <main className="max-w-7xl mx-auto px-5 py-12" data-testid="neighborhood-notfound">
                <h2 className="headline-xl text-4xl">Not on the map.</h2>
                <p className="font-display italic mt-2 text-[var(--muted)]">
                    We don't track that one. <Link to="/neighborhoods" className="underline">See the list →</Link>
                </p>
            </main>
        );
    }
    if (!n) {
        return <main className="max-w-7xl mx-auto px-5 py-12 font-mono text-[var(--muted)]">Loading…</main>;
    }

    const total = n.stats.incidents_30d;

    return (
        <main className="max-w-7xl mx-auto px-5 pt-8 pb-10" data-testid={`neighborhood-page-${slug}`}>
            <Link to="/neighborhoods" className="kicker hover:text-[var(--oxblood)]" data-testid="back-to-neighborhoods">
                ← All Neighborhoods
            </Link>
            <h2 className="headline-xl text-4xl sm:text-5xl md:text-7xl mt-2">{n.name}</h2>
            <p className="font-display italic text-xl md:text-2xl text-[var(--muted)] mt-2 max-w-3xl">
                {n.tagline}
            </p>

            <div className="grid grid-cols-12 gap-6 mt-8">
                <div className="col-span-12 lg:col-span-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                        <div className="editorial-card p-4">
                            <div className="kicker">30-day total</div>
                            <div className="big-num text-5xl mt-1">{total}</div>
                        </div>
                        <div className="editorial-card p-4">
                            <div className="kicker">Last 7 days</div>
                            <div className="big-num text-5xl mt-1">{n.stats.incidents_7d}</div>
                        </div>
                        <div className="editorial-card p-4 col-span-2">
                            <div className="kicker">Districts patrolled</div>
                            <div className="font-display text-2xl mt-1">{n.districts.join(" · ")}</div>
                            <div className="font-mono text-xs text-[var(--muted)] mt-1">
                                Some neighborhoods straddle multiple BPD districts. We aggregate.
                            </div>
                        </div>
                    </div>
                    <CrimeMap incidents={incidents} height="h-[55vh] min-h-[360px] md:h-[480px]" center={mapCenter} zoom={13} />
                </div>
                <aside className="col-span-12 lg:col-span-4">
                    <div className="editorial-card-dark p-6">
                        <div className="kicker text-[var(--amber)]">From the Desk</div>
                        <p className="font-display text-xl leading-snug mt-2 dropcap text-[var(--bg)]">
                            {n.blurb}
                        </p>
                    </div>

                    <div className="mt-6">
                        <div className="kicker">Category breakdown · 30d</div>
                        <ul className="mt-2 border-2 border-[var(--ink)] bg-[var(--surface)]">
                            {n.stats.breakdown.map((b, idx) => (
                                <li
                                    key={b.key}
                                    className={`flex items-center gap-2 p-3 ${idx !== n.stats.breakdown.length - 1 ? "border-b border-[var(--ink)]/25" : ""}`}
                                    data-testid={`breakdown-${b.key}`}
                                >
                                    <span dangerouslySetInnerHTML={{ __html: pinSvgInline(b.key, 22) }} style={{ display: "inline-flex" }} />
                                    <Link to={`/categories/${b.slug}`} className="font-sub uppercase tracking-widest text-xs hover:text-[var(--oxblood)]">
                                        {b.label}
                                    </Link>
                                    <span className="ml-auto font-mono text-sm">{b.count}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </aside>
            </div>

            {/* Recent table */}
            <section className="mt-12" data-testid="recent-table-section">
                <div className="rule mb-3" />
                <div className="kicker">From the Blotter · 25 most recent</div>
                <h3 className="headline-lg text-3xl mt-1">{n.name} reports</h3>
                <div className="mt-4 overflow-x-auto border-2 border-[var(--ink)] bg-[var(--surface)]">
                    <table className="blotter w-full">
                        <thead>
                            <tr>
                                <th>When</th>
                                <th>Category</th>
                                <th>Description</th>
                                <th>Street</th>
                                <th>Dist.</th>
                            </tr>
                        </thead>
                        <tbody>
                            {n.recent.map((r, i) => (
                                <tr key={r.incident_number} data-testid={`recent-row-${i}`}>
                                    <td className="whitespace-nowrap">{formatRelative(r.occurred_on)}</td>
                                    <td>
                                        <span className="inline-flex items-center gap-1.5">
                                            <span dangerouslySetInnerHTML={{ __html: pinSvgInline(r.category, 18) }} style={{ display: "inline-flex" }} />
                                            {CATEGORY_LABELS[r.category]}
                                        </span>
                                    </td>
                                    <td className="font-body text-sm">{r.description}</td>
                                    <td>{r.street || "—"}</td>
                                    <td>{r.district}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </main>
    );
}
