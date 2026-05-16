import { useEffect, useState } from "react";
import { API } from "@/lib/api";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function RotatingPlate({
    height = "h-72",
    intervalMs = 7000,
    showCaption = true,
    captionOverride = null,
    testid = "rotating-plate",
}) {
    const [items, setItems] = useState([]);
    const [idx, setIdx] = useState(0);

    useEffect(() => {
        fetch(`${API}/images/plates`)
            .then((r) => r.json())
            .then((d) => setItems(d.items || []))
            .catch(() => setItems([]));
    }, []);

    useEffect(() => {
        if (items.length < 2) return;
        const t = setInterval(() => setIdx((i) => (i + 1) % items.length), intervalMs);
        return () => clearInterval(t);
    }, [items.length, intervalMs]);

    const current = items[idx];

    return (
        <div data-testid={testid}>
            <div className={`halftone border-2 border-[var(--ink)] shadow-stamp overflow-hidden bg-[var(--surface-dark)] relative ${height}`}>
                {/* Fallback (always under) */}
                <div
                    aria-hidden
                    className="absolute inset-0 flex items-center justify-center text-center px-6"
                    style={{
                        background:
                            "repeating-linear-gradient(45deg, #1c1b1a 0, #1c1b1a 8px, #232220 8px, #232220 16px)",
                    }}
                >
                    <div>
                        <div className="kicker text-[var(--amber)] mb-1">Section A · Plate</div>
                        <div className="font-display italic text-xl text-[var(--bg)] leading-tight">
                            The city, at dusk
                        </div>
                    </div>
                </div>

                {/* Stack all images so we can crossfade between them */}
                {items.map((it, i) => (
                    <img
                        key={it.slug}
                        src={`${BACKEND_URL}${it.src}`}
                        alt={it.where}
                        loading={i === 0 ? "eager" : "lazy"}
                        referrerPolicy="no-referrer"
                        onError={(e) => { e.currentTarget.style.display = "none"; }}
                        className="img-newsprint absolute inset-0 w-full h-full object-cover transition-opacity duration-700"
                        style={{ opacity: i === idx ? 1 : 0 }}
                    />
                ))}
            </div>
            {showCaption && (
                <p className="font-mono text-[11px] text-[var(--muted)] mt-2 uppercase tracking-widest flex items-center justify-between gap-2" data-testid={`${testid}-caption`}>
                    <span>{captionOverride || current?.caption || "Above: somewhere in the Hub."}</span>
                    {items.length > 1 && (
                        <span className="flex gap-1 shrink-0">
                            {items.map((_, i) => (
                                <button
                                    key={i}
                                    onClick={() => setIdx(i)}
                                    aria-label={`Show plate ${i + 1}`}
                                    data-testid={`${testid}-dot-${i}`}
                                    className={`w-2 h-2 border border-[var(--ink)] transition-colors ${
                                        i === idx ? "bg-[var(--oxblood)]" : "bg-transparent hover:bg-[var(--ink)]"
                                    }`}
                                />
                            ))}
                        </span>
                    )}
                </p>
            )}
        </div>
    );
}
