import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchCategory, fetchIncidents } from "@/lib/api";
import { colorFor, formatRelative } from "@/lib/format";
import CrimeMap from "@/components/CrimeMap";
import { pinSvgInline } from "@/components/CrimePin";

export default function CategoryDetail() {
    const { slug } = useParams();
    const [cat, setCat] = useState(null);
    const [incidents, setIncidents] = useState([]);
    const [notFound, setNotFound] = useState(false);

    useEffect(() => {
        setCat(null);
        setIncidents([]);
        setNotFound(false);
        fetchCategory(slug).then(setCat).catch(() => setNotFound(true));
        fetchIncidents({ category: slug, days: 30, limit: 1500 }).then((r) => setIncidents(r.items || []));
    }, [slug]);

    if (notFound) {
        return (
            <main className="max-w-7xl mx-auto px-5 py-12">
                <h2 className="headline-xl text-4xl">Not in the file.</h2>
                <Link to="/map" className="underline mt-3 inline-block">Back to map →</Link>
            </main>
        );
    }
    if (!cat) {
        return <main className="max-w-7xl mx-auto px-5 py-12 font-mono text-[var(--muted)]">Loading…</main>;
    }

    return (
        <main className="max-w-7xl mx-auto px-5 pt-8 pb-10" data-testid={`category-page-${slug}`}>
            <Link to="/" className="kicker hover:text-[var(--oxblood)]">← Front Page</Link>
            <div className="flex items-baseline gap-4 mt-2 flex-wrap">
                <span dangerouslySetInnerHTML={{ __html: pinSvgInline(cat.key, 56) }} style={{ display: "inline-flex" }} />
                <div>
                    <div className="kicker">{cat.bucket} · Crime category</div>
                    <h2 className="headline-xl text-4xl sm:text-5xl md:text-7xl mt-1">{cat.label}</h2>
                </div>
            </div>

            <div className="grid grid-cols-12 gap-6 mt-8">
                <div className="col-span-12 lg:col-span-8">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                        <div className="editorial-card p-4">
                            <div className="kicker">30-day reports</div>
                            <div className="big-num text-5xl mt-1">{cat.stats.incidents_30d}</div>
                        </div>
                        <div className="editorial-card p-4">
                            <div className="kicker">Last 7 days</div>
                            <div className="big-num text-5xl mt-1">{cat.stats.incidents_7d}</div>
                        </div>
                        <div className="editorial-card p-4 col-span-2 md:col-span-1">
                            <div className="kicker">Top district</div>
                            <div className="font-display text-xl leading-tight mt-1">
                                {cat.stats.by_district[0]?.district || "—"}
                            </div>
                            <div className="font-mono text-xs text-[var(--muted)] mt-1">
                                {cat.stats.by_district[0]?.label || ""}
                            </div>
                        </div>
                    </div>
                    <CrimeMap incidents={incidents} height="h-[55vh] min-h-[360px] md:h-[480px]" />
                </div>
                <aside className="col-span-12 lg:col-span-4">
                    <div className="editorial-card p-5">
                        <div className="kicker">Definition</div>
                        <p className="font-body text-base leading-relaxed mt-2">{cat.definition}</p>
                    </div>
                    <div className="editorial-card-dark p-5 mt-4">
                        <div className="kicker text-[var(--amber)]">Boston note</div>
                        <p className="font-display italic text-lg leading-snug mt-2">{cat.boston_note}</p>
                    </div>
                    <div className="mt-4">
                        <div className="kicker">By district · 30d</div>
                        <ul className="mt-2 border-2 border-[var(--ink)] bg-[var(--surface)]">
                            {cat.stats.by_district.slice(0, 10).map((d, i) => (
                                <li key={d.district} className={`flex items-center justify-between gap-3 p-3 ${i !== Math.min(9, cat.stats.by_district.length - 1) ? "border-b border-[var(--ink)]/25" : ""}`}>
                                    <span className="font-mono text-xs">{d.district}</span>
                                    <span className="font-body text-xs flex-1 text-[var(--muted)] truncate">{d.label}</span>
                                    <span className="font-mono text-sm">{d.count}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </aside>
            </div>

            <section className="mt-12">
                <div className="rule mb-3" />
                <div className="kicker">Recent {cat.label.toLowerCase()} reports</div>
                <div className="mt-4 overflow-x-auto border-2 border-[var(--ink)] bg-[var(--surface)]">
                    <table className="blotter w-full">
                        <thead>
                            <tr><th>When</th><th>Description</th><th>Street</th><th>Dist.</th></tr>
                        </thead>
                        <tbody>
                            {cat.recent.map((r) => (
                                <tr key={r.incident_number}>
                                    <td className="whitespace-nowrap">{formatRelative(r.occurred_on)}</td>
                                    <td>{r.description}</td>
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
