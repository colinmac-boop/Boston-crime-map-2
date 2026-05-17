import { useEffect, useState } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { geocodeAddress, fetchIncidentsNear } from "@/lib/api";

const RADIUS_OPTIONS = [
    { v: 0.1, l: "1/10 mi" },
    { v: 0.25, l: "1/4 mi" },
    { v: 0.5, l: "1/2 mi" },
    { v: 1, l: "1 mi" },
];

export default function AddressSearch({ onResult, onClear, days = 90, initialQuery = "", category = "" }) {
    const [q, setQ] = useState(initialQuery);
    const [radius, setRadius] = useState(0.25);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [active, setActive] = useState(null); // { hit, near }
    const [autoRan, setAutoRan] = useState(false);

    const submit = async (e) => {
        e?.preventDefault();
        const query = q.trim();
        if (!query) return;
        setLoading(true);
        setError("");
        try {
            const hit = await geocodeAddress(query);
            const near = await fetchIncidentsNear({
                lat: hit.lat,
                lng: hit.lng,
                radius_mi: radius,
                days,
                category,
            });
            setActive({ hit, near });
            onResult?.({ hit, near, radius });
        } catch (err) {
            const status = err?.response?.status;
            if (status === 404) {
                setError("No Boston-area match. Try a more specific address.");
            } else {
                setError("Couldn't reach the geocoder. Try again in a moment.");
            }
            setActive(null);
            onClear?.();
        } finally {
            setLoading(false);
        }
    };

    const clear = () => {
        setQ("");
        setError("");
        setActive(null);
        onClear?.();
    };

    // Auto-fire search if initialQuery was provided (deep-link from homepage)
    useEffect(() => {
        if (initialQuery && !autoRan) {
            setAutoRan(true);
            submit();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialQuery]);

    // Re-search when the radius or the map crime filter changes after an initial result.
    const refetchNear = async (nextRadius = radius) => {
        if (!active) return;
        setLoading(true);
        try {
            const near = await fetchIncidentsNear({
                lat: active.hit.lat,
                lng: active.hit.lng,
                radius_mi: nextRadius,
                days,
                category,
            });
            const next = { ...active, near };
            setActive(next);
            onResult?.({ hit: active.hit, near, radius: nextRadius });
        } catch {
            // keep prior result
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refetchNear(radius);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [category, days]);

    const setRadiusAndRefetch = async (r) => {
        setRadius(r);
        refetchNear(r);
    };

    return (
        <div className="border-2 border-[var(--ink)] bg-[var(--surface)]" data-testid="address-search">
            <form onSubmit={submit} className="p-4">
                <div className="flex items-baseline justify-between mb-2 gap-2">
                    <div className="kicker">Address lookup</div>
                    {active && (
                        <button
                            type="button"
                            onClick={clear}
                            className="font-mono text-[11px] uppercase tracking-widest text-[var(--muted)] hover:text-[var(--oxblood)]"
                            data-testid="address-clear"
                        >
                            Clear ×
                        </button>
                    )}
                </div>
                <div className="flex flex-wrap gap-2">
                    <div className="flex-1 min-w-[240px] flex items-center border-2 border-[var(--ink)] bg-[var(--bg)]">
                        <Search size={16} className="ml-2.5 shrink-0" />
                        <input
                            type="text"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                            placeholder="700 Boylston St, or Fenway Park, or Dorchester Ave"
                            className="w-full bg-transparent px-2 py-2 font-mono text-sm outline-none placeholder:text-[var(--muted)]"
                            data-testid="address-input"
                            autoComplete="off"
                            spellCheck={false}
                        />
                        {q && !loading && (
                            <button
                                type="button"
                                onClick={() => setQ("")}
                                aria-label="Clear input"
                                className="px-2 text-[var(--muted)] hover:text-[var(--ink)]"
                                data-testid="address-input-clear"
                            >
                                <X size={14} />
                            </button>
                        )}
                    </div>
                    <button
                        type="submit"
                        disabled={loading || !q.trim()}
                        className="btn-ink disabled:opacity-50 disabled:cursor-not-allowed"
                        data-testid="address-submit"
                    >
                        {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                        {loading ? "Looking…" : "Look up"}
                    </button>
                </div>
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                    <span className="kicker">Radius</span>
                    {RADIUS_OPTIONS.map((o) => (
                        <button
                            key={o.v}
                            type="button"
                            onClick={() => setRadiusAndRefetch(o.v)}
                            disabled={loading}
                            data-testid={`address-radius-${o.v}`}
                            className={`px-2.5 py-1 font-sub uppercase tracking-widest text-[11px] border-2 border-[var(--ink)] ${
                                radius === o.v
                                    ? "bg-[var(--ink)] text-[var(--bg)]"
                                    : "bg-[var(--bg)] hover:bg-[var(--ink)] hover:text-[var(--bg)]"
                            }`}
                        >
                            {o.l}
                        </button>
                    ))}
                </div>
                {error && (
                    <div className="mt-3 font-mono text-xs text-[var(--oxblood)]" data-testid="address-error">
                        {error}
                    </div>
                )}
            </form>

            {active && (
                <div className="border-t-2 border-[var(--ink)] bg-[var(--surface-dark)] text-[var(--bg)] p-4" data-testid="address-result">
                    <div className="kicker text-[var(--amber)]">Reading on</div>
                    <div className="font-display text-xl md:text-2xl leading-tight mt-1" data-testid="address-result-label">
                        {active.hit.label || active.hit.display_name}
                    </div>
                    <div className="font-mono text-[11px] text-neutral-400 mt-1">
                        {active.hit.display_name}
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-3">
                        <div>
                            <div className="kicker text-[var(--amber)]">Within {radius} mi · {days}d{category ? ` · ${category}` : ""}</div>
                            <div className="big-num text-5xl text-[var(--bg)] mt-1" data-testid="address-result-count">
                                {active.near.count}
                            </div>
                            <div className="font-mono text-[10px] text-neutral-400 uppercase tracking-widest">
                                Reports + story pins
                            </div>
                        </div>
                        <div>
                            <div className="kicker text-[var(--amber)]">Top categories</div>
                            <ul className="mt-1 font-mono text-xs text-neutral-200 space-y-0.5">
                                {active.near.breakdown.slice(0, 4).map((b) => (
                                    <li key={b.key} className="flex justify-between gap-2" data-testid={`address-result-cat-${b.key}`}>
                                        <span>{b.label}</span>
                                        <span className="text-neutral-400 tabular-nums">{b.count}</span>
                                    </li>
                                ))}
                                {active.near.breakdown.length === 0 && (
                                    <li className="text-neutral-400">Quiet block. Lock the back door anyway.</li>
                                )}
                            </ul>
                        </div>
                    </div>
                    {active.near.items[0] && (
                        <div className="mt-4 pt-3 border-t border-neutral-700 font-mono text-[11px] text-neutral-400">
                            Nearest report: <span className="text-[var(--amber)]">{active.near.items[0].distance_mi} mi</span>
                            {" · "}{active.near.items[0].description}
                            {" · "}{active.near.items[0].street || "Boston"}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
