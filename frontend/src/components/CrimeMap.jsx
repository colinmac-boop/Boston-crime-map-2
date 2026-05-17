import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster";
import { CATEGORY_COLORS, CATEGORY_LABELS, formatRelative } from "@/lib/format";
import { pinIcon, pinSvgInline } from "@/components/CrimePin";

// CartoDB Dark Matter — dark, gritty, civic.
const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTR =
    '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a> · Incidents via <a href="https://data.boston.gov/">BPD Open Data</a>; stories via <a href="https://police.boston.gov/stories-in-the-news/">BPD</a>, <a href="https://www.universalhub.com/crime/index.html">Universal Hub</a>, <a href="https://www.boston25news.com/">Boston 25 News</a>, and <a href="https://www.wcvb.com/">WCVB</a>';

const BOSTON_CENTER = [42.3408, -71.0892];

function dotIcon(category) {
    return pinIcon(category);
}

function popupHtml(inc) {
    const cat = CATEGORY_LABELS[inc.category] || "Incident";
    const when = formatRelative(inc.occurred_on);
    const source = inc.source_name ? ` · ${escapeHtml(inc.source_name)}` : "";
    const link = inc.source_url
        ? `<div class="pop-meta"><a href="${escapeHtml(inc.source_url)}" target="_blank" rel="noreferrer">Read source story →</a></div>`
        : "";
    return `
        <div data-testid="map-popup-${inc.incident_number}">
            <div class="pop-cat">${cat}${inc.shooting ? " · Shots fired" : ""}${source}</div>
            <div class="pop-desc">${escapeHtml(inc.description)}</div>
            <div class="pop-meta">${escapeHtml(inc.street || "Boston")} · ${escapeHtml(when)} · District ${escapeHtml(inc.district)}</div>
            ${link}
        </div>
    `;
}

function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[c]));
}

export default function CrimeMap({
    incidents = [],
    height = "560px",
    center = BOSTON_CENTER,
    zoom = 12,
    cluster = true,
    interactive = true,
    autoFit = false,
    searchPin = null,        // { lat, lng, label }
    searchRadiusMi = null,   // number, draws a circle if set with searchPin
}) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const layerRef = useRef(null);
    const searchLayerRef = useRef(null);

    // Detect touch / coarse pointer once on mount
    const isTouch = useMemo(
        () => typeof window !== "undefined" &&
            (window.matchMedia?.("(pointer: coarse)").matches ||
             "ontouchstart" in window),
        []
    );

    // On mobile, dragging is gated behind a tap so the page can scroll past
    // the map. Once activated, it stays active until you scroll the page away
    // from the map and back, or unmount.
    const [touchActive, setTouchActive] = useState(false);

    // Initialize map once
    useEffect(() => {
        if (!containerRef.current || mapRef.current) return;
        const map = L.map(containerRef.current, {
            center,
            zoom,
            zoomControl: interactive,
            scrollWheelZoom: interactive,
            dragging: interactive,
            doubleClickZoom: interactive,
            boxZoom: interactive,
            keyboard: interactive,
            tap: interactive,
            attributionControl: true,
            // Note: preferCanvas:true is incompatible with our div-icon markers
            // and triggers an _leaflet_pos undefined crash during zoom — leave
            // it off and let Leaflet use the SVG/HTML overlay panes.
            gestureHandling: true,
            gestureHandlingOptions: {
                text: {
                    touch: "Use two fingers to move the map",
                    scroll: "Use Ctrl + scroll to zoom the map",
                    scrollMac: "Use \u2318 + scroll to zoom the map",
                },
                duration: 1000,
            },
        });
        L.tileLayer(TILE_URL, {
            attribution: TILE_ATTR,
            subdomains: "abcd",
            maxZoom: 19,
        }).addTo(map);
        mapRef.current = map;

        // Make sure the container has a measured size before any zoom/pan
        // handler runs. Without this, scroll-wheel zoom on a freshly mounted
        // map throws "el._leaflet_pos is undefined" because the map pane
        // never got positioned. Two passes — one immediately, one after the
        // next paint — handles both initial mount and post-route mounts.
        const t1 = setTimeout(() => mapRef.current && mapRef.current.invalidateSize(), 0);
        const t2 = setTimeout(() => mapRef.current && mapRef.current.invalidateSize(), 250);

        // Re-validate when the container or window resizes (orientation flip
        // on mobile, dev-tools toggle, etc.)
        let ro;
        if (typeof ResizeObserver !== "undefined") {
            ro = new ResizeObserver(() => {
                if (mapRef.current) mapRef.current.invalidateSize();
            });
            ro.observe(containerRef.current);
        }
        const onResize = () => mapRef.current && mapRef.current.invalidateSize();
        window.addEventListener("resize", onResize);
        window.addEventListener("orientationchange", onResize);

        return () => {
            clearTimeout(t1);
            clearTimeout(t2);
            window.removeEventListener("resize", onResize);
            window.removeEventListener("orientationchange", onResize);
            if (ro) ro.disconnect();
            map.off();   // detach every listener so no stale wheel/touch
            map.remove(); // event fires after unmount
            mapRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Recenter when the center prop changes (after incidents load on detail pages)
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return;
        // Don't recenter if the search pin is driving the view — it owns the
        // viewport while a search is active.
        if (searchPin) return;
        try {
            map.setView(center, zoom, { animate: true });
        } catch (e) {
            // Map mid-init — recenter on next tick after panes are positioned
            setTimeout(() => {
                if (mapRef.current && !searchPin) {
                    try { mapRef.current.setView(center, zoom); } catch {}
                }
            }, 150);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [center[0], center[1], zoom, searchPin]);

    // Update markers when incidents change
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return;
        if (layerRef.current) {
            map.removeLayer(layerRef.current);
            layerRef.current = null;
        }

        const group = cluster
            ? L.markerClusterGroup({
                  showCoverageOnHover: false,
                  spiderfyOnMaxZoom: true,
                  disableClusteringAtZoom: 16,
                  maxClusterRadius: 48,
                  iconCreateFunction: (c) => {
                      const n = c.getChildCount();
                      return L.divIcon({
                          html: `<div style="background:#1c1b1a;color:#f4f1ea;border:2px solid #8b1c1c;width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Oswald',sans-serif;font-weight:700;font-size:13px;letter-spacing:0.05em;box-shadow:3px 3px 0 #8b1c1c">${n}</div>`,
                          className: "",
                          iconSize: [38, 38],
                      });
                  },
              })
            : L.layerGroup();

        const validPoints = [];
        incidents.forEach((inc) => {
            if (!inc.lat || !inc.lng) return;
            validPoints.push([inc.lat, inc.lng]);
            const marker = L.marker([inc.lat, inc.lng], {
                icon: dotIcon(inc.category),
                title: inc.description,
            });
            marker.bindPopup(popupHtml(inc));
            group.addLayer(marker);
        });

        group.addTo(map);
        layerRef.current = group;

        if (autoFit && !searchPin && validPoints.length > 0) {
            setTimeout(() => {
                if (!mapRef.current) return;
                try {
                    mapRef.current.invalidateSize();
                    if (validPoints.length === 1) {
                        mapRef.current.setView(validPoints[0], 15, { animate: true });
                    } else {
                        mapRef.current.fitBounds(L.latLngBounds(validPoints), {
                            padding: [36, 36],
                            maxZoom: 15,
                            animate: true,
                        });
                    }
                } catch {}
            }, 80);
        }
    }, [incidents, cluster, autoFit, searchPin]);

    // Search pin + radius circle
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return;
        if (searchLayerRef.current) {
            map.removeLayer(searchLayerRef.current);
            searchLayerRef.current = null;
        }
        if (!searchPin) return;

        const group = L.layerGroup();

        // The "you searched here" marker — a distinct cream-on-ink star pin
        const pinHtml = `
<svg xmlns="http://www.w3.org/2000/svg" width="44" height="58" viewBox="0 0 40 52" overflow="visible">
    <path d="M20 49 L8 28 C6 22, 8 16, 12 12 C 15 9, 18 8, 20 8 C 22 8, 25 9, 28 12 C 32 16, 34 22, 32 28 Z"
          transform="translate(2.5,2.5)" fill="#0f0f10" opacity="0.5"/>
    <path d="M20 49 L8 28 C6 22, 8 16, 12 12 C 15 9, 18 8, 20 8 C 22 8, 25 9, 28 12 C 32 16, 34 22, 32 28 Z"
          fill="#1c1b1a" stroke="#d9772b" stroke-width="2.5" stroke-linejoin="miter"/>
    <circle cx="20" cy="20" r="11" fill="#d9772b" stroke="#1c1b1a" stroke-width="1.5"/>
    <path d="M20 13 L22 18 L27 18 L23 21.5 L24.5 26.5 L20 23.5 L15.5 26.5 L17 21.5 L13 18 L18 18 Z"
          fill="#1c1b1a"/>
</svg>`;
        const pinIconHere = L.divIcon({
            className: "crime-pin",
            html: pinHtml,
            iconSize: [44, 58],
            iconAnchor: [22, 55],
            popupAnchor: [0, -50],
        });
        const m = L.marker([searchPin.lat, searchPin.lng], { icon: pinIconHere, zIndexOffset: 1000 });
        if (searchPin.label) {
            m.bindPopup(
                `<div><div class="pop-cat">Your search</div><div class="pop-desc">${String(searchPin.label).replace(/[<>]/g, "")}</div></div>`
            );
        }
        group.addLayer(m);

        if (searchRadiusMi && searchRadiusMi > 0) {
            const meters = searchRadiusMi * 1609.34;
            L.circle([searchPin.lat, searchPin.lng], {
                radius: meters,
                color: "#d9772b",
                weight: 2,
                opacity: 0.95,
                fillColor: "#d9772b",
                fillOpacity: 0.08,
                dashArray: "6 4",
            }).addTo(group);
        }

        group.addTo(map);
        searchLayerRef.current = group;
        // Fit the radius into view — invalidate size first so the freshly
        // sized container has its panes positioned before fitBounds runs.
        try {
            map.invalidateSize();
            if (searchRadiusMi && searchRadiusMi > 0) {
                const meters = searchRadiusMi * 1609.34;
                map.fitBounds(
                    L.latLng(searchPin.lat, searchPin.lng).toBounds(meters * 2.4),
                    { animate: true }
                );
            } else {
                map.setView([searchPin.lat, searchPin.lng], 16, { animate: true });
            }
        } catch {
            // Try again after the next paint
            setTimeout(() => {
                if (!mapRef.current) return;
                try {
                    mapRef.current.invalidateSize();
                    mapRef.current.setView([searchPin.lat, searchPin.lng], 15);
                } catch {}
            }, 200);
        }
    }, [searchPin, searchRadiusMi]);

    const counts = useMemo(() => {
        const c = {};
        incidents.forEach((i) => {
            c[i.category] = (c[i.category] || 0) + 1;
        });
        return c;
    }, [incidents]);

    // Support both fixed pixel heights ("560px") and Tailwind responsive
    // classes ("h-[60vh] md:h-[640px]").
    const heightIsClass = typeof height === "string" && /[a-z-]/.test(height) && !height.endsWith("px") && !height.endsWith("vh");
    return (
        <div className="relative border-2 border-[var(--ink)] shadow-stamp" data-testid="crime-map">
            <div
                ref={containerRef}
                className={heightIsClass ? height : ""}
                style={heightIsClass ? { width: "100%" } : { height, width: "100%" }}
            />

            {/* Tap-to-activate overlay for touch devices. Lets one-finger
                page scroll pass through the map until the user explicitly
                taps in. */}
            {isTouch && interactive && !touchActive && (
                <button
                    type="button"
                    onClick={() => setTouchActive(true)}
                    className="absolute inset-0 z-[500] flex items-center justify-center bg-[var(--ink)]/40 backdrop-blur-[1px] text-[var(--bg)] font-sub uppercase tracking-widest text-sm cursor-pointer"
                    data-testid="map-tap-activate"
                    aria-label="Activate map controls"
                >
                    <span className="px-4 py-2.5 border-2 border-[var(--bg)] bg-[var(--ink)]/90">
                        Tap to use map · Pinch to zoom
                    </span>
                </button>
            )}
            {isTouch && interactive && touchActive && (
                <button
                    type="button"
                    onClick={() => setTouchActive(false)}
                    className="absolute z-[450] top-2 right-2 px-2 py-1 bg-[var(--surface)] border-2 border-[var(--ink)] font-sub uppercase tracking-widest text-[10px] hover:bg-[var(--ink)] hover:text-[var(--bg)]"
                    data-testid="map-tap-deactivate"
                >
                    Lock map ✕
                </button>
            )}
            {/* Map overlay legend — collapsible on mobile */}
            <details
                className="absolute z-[400] left-2 bottom-2 bg-[var(--surface)] border-2 border-[var(--ink)] max-w-[300px] [&[open]>summary]:border-b-2 [&[open]>summary]:border-[var(--ink)]/40"
                data-testid="map-legend"
            >
                <summary className="px-3 py-1.5 cursor-pointer list-none flex items-center gap-2 select-none">
                    <span className="kicker">Legend · 30d</span>
                    <span className="font-mono text-[10px] text-[var(--muted)] ml-auto" aria-hidden>tap ▾</span>
                </summary>
                <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono px-3 py-2 max-h-[40vh] overflow-y-auto">
                    {Object.entries(CATEGORY_LABELS).map(([k, label]) => (
                        <li key={k} className="flex items-center gap-1.5">
                            <span
                                dangerouslySetInnerHTML={{ __html: pinSvgInline(k, 22) }}
                                style={{ display: "inline-flex", alignItems: "center" }}
                            />
                            <span className="truncate">{label}</span>
                            <span className="text-[var(--muted)] ml-auto tabular-nums">{counts[k] || 0}</span>
                        </li>
                    ))}
                </ul>
            </details>
        </div>
    );
}
