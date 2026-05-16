// Modern flat SVG pushpin markers for Leaflet, inspired by SpotCrime's
// illustrated-icon approach but redrawn for our oxblood/navy/cream scheme.
//
// Anatomy of each pin:
//   - Teardrop body filled with the category color
//   - Cream circular face up top
//   - Ink-black outline (2px) for crispness on dark map tiles
//   - Centered glyph inside the face (varies per category)
//   - Drop shadow (offset) for the brutalist feel

import L from "leaflet";
import { CATEGORY_COLORS } from "@/lib/format";

// Each glyph is rendered inside a 24x24 viewBox, centered in the pin face.
// They are deliberately simple, geometric, and editorial — not literal.
const GLYPHS = {
    homicide: `
        <path d="M6 6 L18 18 M18 6 L6 18" stroke="#0f0f10" stroke-width="2.6" stroke-linecap="round"/>
        <circle cx="12" cy="12" r="9" fill="none" stroke="#0f0f10" stroke-width="1.2"/>
    `,
    // Crosshair / target — SpotCrime's shooting icon translated to flat geometry
    shooting: `
        <circle cx="12" cy="12" r="9" fill="none" stroke="#0f0f10" stroke-width="2"/>
        <circle cx="12" cy="12" r="4.5" fill="#0f0f10"/>
        <line x1="12" y1="1.5" x2="12" y2="6" stroke="#0f0f10" stroke-width="2" stroke-linecap="round"/>
        <line x1="12" y1="18" x2="12" y2="22.5" stroke="#0f0f10" stroke-width="2" stroke-linecap="round"/>
        <line x1="1.5" y1="12" x2="6" y2="12" stroke="#0f0f10" stroke-width="2" stroke-linecap="round"/>
        <line x1="18" y1="12" x2="22.5" y2="12" stroke="#0f0f10" stroke-width="2" stroke-linecap="round"/>
    `,
    // Mask — pulled-up hood silhouette
    robbery: `
        <path d="M4 14 C 4 8, 8 4, 12 4 C 16 4, 20 8, 20 14 L 20 20 L 4 20 Z"
              fill="#0f0f10"/>
        <rect x="6.5" y="11.5" width="4" height="2.5" rx="0.5" fill="#f4f1ea"/>
        <rect x="13.5" y="11.5" width="4" height="2.5" rx="0.5" fill="#f4f1ea"/>
    `,
    // Fist — assault
    assault: `
        <path d="M6 9 C6 7.5, 7 6.5, 8.5 6.5 L15 6.5 C16.5 6.5, 17.5 7.5, 17.5 9 L17.5 16 C17.5 17.5, 16.5 18.5, 15 18.5 L9 18.5 C7.5 18.5, 6 17.5, 6 16 Z"
              fill="#0f0f10"/>
        <line x1="9" y1="10" x2="9" y2="14" stroke="#f4f1ea" stroke-width="1.2"/>
        <line x1="11.5" y1="10" x2="11.5" y2="14" stroke="#f4f1ea" stroke-width="1.2"/>
        <line x1="14" y1="10" x2="14" y2="14" stroke="#f4f1ea" stroke-width="1.2"/>
    `,
    // Open door — burglary
    burglary: `
        <rect x="6" y="4" width="10" height="16" fill="none" stroke="#0f0f10" stroke-width="2"/>
        <path d="M16 4 L20 6 L20 22 L16 20 Z" fill="#0f0f10"/>
        <circle cx="18" cy="13" r="0.9" fill="#f4f1ea"/>
    `,
    // Hand grabbing — larceny
    larceny: `
        <path d="M4 11 L9 11 L9 7 C9 6, 10 5, 11 5 C12 5, 13 6, 13 7 L13 11 L18 13 L18 18 L8 18 L4 14 Z"
              fill="#0f0f10"/>
        <line x1="11" y1="7" x2="11" y2="11" stroke="#f4f1ea" stroke-width="1.2"/>
    `,
    // Car silhouette — vehicle theft
    vehicle_theft: `
        <path d="M3 14 L4.5 9 C5 8, 6 7.5, 7 7.5 L17 7.5 C18 7.5, 19 8, 19.5 9 L21 14 L21 17 L19 17 L19 15 L5 15 L5 17 L3 17 Z"
              fill="#0f0f10"/>
        <circle cx="7" cy="16.5" r="1.8" fill="#f4f1ea" stroke="#0f0f10" stroke-width="0.8"/>
        <circle cx="17" cy="16.5" r="1.8" fill="#f4f1ea" stroke="#0f0f10" stroke-width="0.8"/>
    `,
    // Spray can — vandalism
    vandalism: `
        <rect x="8.5" y="9" width="7" height="11" rx="0.8" fill="#0f0f10"/>
        <rect x="9.5" y="6" width="5" height="3" fill="#0f0f10"/>
        <line x1="12" y1="4" x2="12" y2="6" stroke="#0f0f10" stroke-width="2" stroke-linecap="round"/>
        <circle cx="17" cy="5" r="0.7" fill="#0f0f10"/>
        <circle cx="19" cy="7" r="0.5" fill="#0f0f10"/>
        <circle cx="18.5" cy="4" r="0.4" fill="#0f0f10"/>
    `,
    // Pill capsule — drugs
    drugs: `
        <path d="M5 12 C 5 9.5, 7 7.5, 9.5 7.5 L 14.5 7.5 C 17 7.5, 19 9.5, 19 12 C 19 14.5, 17 16.5, 14.5 16.5 L 9.5 16.5 C 7 16.5, 5 14.5, 5 12 Z"
              fill="#0f0f10"/>
        <path d="M5 12 C 5 9.5, 7 7.5, 9.5 7.5 L 12 7.5 L 12 16.5 L 9.5 16.5 C 7 16.5, 5 14.5, 5 12 Z"
              fill="#f4f1ea"/>
    `,
    // Exclamation in a triangle — other
    other: `
        <path d="M12 4 L 21 19 L 3 19 Z" fill="#0f0f10"/>
        <line x1="12" y1="9" x2="12" y2="14" stroke="#f4f1ea" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="12" cy="16.5" r="1" fill="#f4f1ea"/>
    `,
};

// Pin SVG: teardrop body (40x52 viewBox), cream face circle at top, glyph
// inside, shadow offset for the brutalist feel.
//
// Sizes: standard markers 32x42 (pin face = 28dia), large (violent) 38x50.
function buildPinSvg(category, { large = false } = {}) {
    const color = CATEGORY_COLORS[category] || CATEGORY_COLORS.other;
    const glyph = GLYPHS[category] || GLYPHS.other;
    const w = large ? 38 : 32;
    const h = large ? 50 : 42;

    return `
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 40 52" overflow="visible">
    <!-- Hard offset shadow for brutalist depth -->
    <path d="M20 49 L8 28 C6 22, 8 16, 12 12 C 15 9, 18 8, 20 8 C 22 8, 25 9, 28 12 C 32 16, 34 22, 32 28 Z"
          transform="translate(2.5,2.5)" fill="#0f0f10" opacity="0.45"/>
    <!-- Pin body -->
    <path d="M20 49 L8 28 C6 22, 8 16, 12 12 C 15 9, 18 8, 20 8 C 22 8, 25 9, 28 12 C 32 16, 34 22, 32 28 Z"
          fill="${color}" stroke="#0f0f10" stroke-width="2" stroke-linejoin="miter"/>
    <!-- Cream face -->
    <circle cx="20" cy="20" r="11" fill="#f4f1ea" stroke="#0f0f10" stroke-width="1.5"/>
    <!-- Glyph, scaled into the face -->
    <g transform="translate(8 8) scale(1)">
        ${glyph}
    </g>
</svg>
    `.trim();
}

const CACHE = {};

export function pinIcon(category, opts = {}) {
    const key = `${category}_${opts.large ? "L" : "S"}`;
    if (CACHE[key]) return CACHE[key];

    const large = opts.large || category === "homicide" || category === "shooting";
    const svg = buildPinSvg(category, { large });
    const w = large ? 38 : 32;
    const h = large ? 50 : 42;

    const icon = L.divIcon({
        className: "crime-pin",
        html: svg,
        iconSize: [w, h],
        iconAnchor: [w / 2, h - 3], // anchor at the tip of the teardrop
        popupAnchor: [0, -h + 8],
    });
    CACHE[key] = icon;
    return icon;
}

// Reusable HTML snippet for the legend / category cards
export function pinSvgInline(category, sizePx = 28) {
    const svg = buildPinSvg(category);
    return `<span style="display:inline-flex;width:${sizePx * 32 / 42}px;height:${sizePx}px;align-items:center;justify-content:center">${svg}</span>`;
}
