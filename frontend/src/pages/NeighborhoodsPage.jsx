import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchNeighborhoods } from "@/lib/api";

export default function NeighborhoodsPage() {
    const [items, setItems] = useState([]);
    useEffect(() => {
        fetchNeighborhoods().then((r) => setItems(r.items || []));
    }, []);
    return (
        <main className="max-w-7xl mx-auto px-5 pt-8 pb-10" data-testid="neighborhoods-page">
            <div className="kicker">Section · Neighborhoods</div>
            <h2 className="headline-xl text-4xl md:text-6xl mt-1">Nineteen Bostons</h2>
            <p className="font-display italic text-[var(--muted)] mt-2 max-w-2xl">
                Every one of them is the real one. Ask anyone who lives there.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">
                {items.map((n, i) => (
                    <Link
                        key={n.slug}
                        to={`/neighborhoods/${n.slug}`}
                        className="editorial-card p-5 block paperdrop"
                        style={{ animationDelay: `${i * 25}ms` }}
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
                {items.length === 0 && (
                    <div className="font-mono text-[var(--muted)]">Loading the neighborhoods…</div>
                )}
            </div>
        </main>
    );
}
