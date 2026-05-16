import { useEffect, useState } from "react";
import { fetchWickedPicks } from "@/lib/api";
import { Link } from "react-router-dom";
import RotatingPlate from "@/components/RotatingPlate";
import { pinSvgInline } from "@/components/CrimePin";

export default function WickedPicksPage() {
    const [picks, setPicks] = useState([]);
    const [asOf, setAsOf] = useState("");
    useEffect(() => {
        fetchWickedPicks(10).then((r) => {
            setPicks(r.items || []);
            setAsOf(r.as_of || "");
        });
    }, []);

    const dateLabel = asOf
        ? new Date(asOf).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })
        : "";

    return (
        <main className="max-w-7xl mx-auto px-5 pt-8 pb-10" data-testid="wicked-picks-page">
            <div className="kicker">Section · Editorial</div>
            <div className="flex items-end gap-6 flex-wrap">
                <h2 className="headline-xl text-4xl sm:text-5xl md:text-8xl mt-1">Wicked Picks</h2>
                <p className="font-display italic text-xl text-[var(--muted)] mb-3">
                    Filed {dateLabel}
                </p>
            </div>
            <p className="font-display italic text-xl md:text-2xl mt-3 max-w-3xl">
                A short, opinionated read of what's in the BPD file this week. We pick from each category. We do not invent details. The dry parts are us; the facts are theirs.
            </p>

            {/* Featured rotating image strip */}
            <div className="mt-8">
                <RotatingPlate height="h-48 md:h-64" testid="picks-plate" />
            </div>

            <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-6">
                {picks.map((p, i) => (
                    <article
                        key={i}
                        className={`p-6 paperdrop ${i % 2 === 0 ? "editorial-card" : "editorial-card-dark"}`}
                        style={{ animationDelay: `${i * 50}ms` }}
                        data-testid={`pick-row-${i}`}
                    >
                        <div className="flex items-center gap-3 mb-3">
                            <span
                                dangerouslySetInnerHTML={{ __html: pinSvgInline(p.category.key, 30) }}
                                style={{ display: "inline-flex", alignItems: "center" }}
                            />
                            <Link
                                to={`/categories/${p.category.slug}`}
                                className={`font-sub uppercase tracking-widest text-xs hover:underline ${
                                    i % 2 === 0 ? "text-[var(--oxblood)]" : "text-[var(--amber)]"
                                }`}
                            >
                                {p.category.label}
                            </Link>
                            <span className={`font-mono text-[10px] ml-auto ${i % 2 === 0 ? "text-[var(--muted)]" : "text-neutral-400"}`}>
                                {p.when}
                            </span>
                        </div>
                        <h3 className={`font-display text-3xl md:text-4xl leading-tight ${i % 2 === 0 ? "" : "text-[var(--bg)]"}`}>
                            {p.headline}
                        </h3>
                        <p className={`font-display italic text-lg md:text-xl mt-3 leading-snug ${i % 2 === 0 ? "" : "text-neutral-200"}`}>
                            "{p.commentary}"
                        </p>
                        <div className={`mt-5 pt-3 border-t font-mono text-xs uppercase tracking-widest ${
                            i % 2 === 0 ? "border-[var(--ink)]/30 text-[var(--muted)]" : "border-neutral-700 text-neutral-400"
                        }`}>
                            <span className="block">{p.incident.description}</span>
                            <span className="block mt-1">{p.where}</span>
                        </div>
                    </article>
                ))}
                {picks.length === 0 && (
                    <div className="font-mono text-[var(--muted)]">Loading picks…</div>
                )}
            </div>
        </main>
    );
}
