# The Boston Crime Map — PRD

## Original Problem Statement
Build a Boston crime map paired with a wicked-dry editorial voice, inspired by lexingtoncrime.com / austincrimemap.com (data) and baltimoreday.com / wickedlocal.com (voice + sensibility). Gritty, interactive, beautiful, mobile-first. Cannot look AI-generated. Must include reality without offending Boston citizens.

## User Choices (locked in)
- Data: Boston PD official open data (data.boston.gov CKAN resource `b973d8cb-eeb2-4e7e-99da-c92938efc9c0`)
- Tone: wicked dry — deadpan, observational, never punching down
- Email alerts: deferred
- Map tech: Leaflet + OSM (CartoDB Dark Matter tiles) with leaflet-gesture-handling for mobile
- Scope: full v1 + address search + self-hosted Boston imagery + modern SVG pushpin markers + mobile-first
- Imagery: self-hosted at `/api/static/images/` (Fenway scoreboard, Beacon Hill brownstones, Zakim Bridge at night, Boston Harbor / Charles River aerial)
- Pin markers: modern SpotCrime-style teardrop pins with category glyphs

## Architecture
- **Backend**: FastAPI on port 8001 under `/api`. Pulls up to 8,000 recent BPD incidents via CKAN SQL, normalizes + categorizes + geo-filters, caches in MongoDB 1hr TTL. OSM Nominatim geocoding proxy with 30d cache + Boston viewbox bias. Haversine-based "incidents near point" with bounding-box pre-filter. Static `/api/static/images/` for self-hosted Boston imagery.
- **Frontend**: React (CRA) + Tailwind + custom CSS, React Router, Leaflet + react-fast-marquee + leaflet-gesture-handling + leaflet.markercluster. Cream newsprint background (#F4F1EA) + SVG grain overlay, Playfair Display + Oswald + IBM Plex Sans/Mono, oxblood (#8B1C1C) + harbor navy (#14253A) + amber (#D9772B) + ink. Brutalist 4px offset shadows.

## Endpoints (`/api/...`)
- `GET /health`, `GET /`
- `POST /refresh` — force BPD re-fetch
- `GET /incidents` — params: category, district, neighborhood, days, limit
- `GET /incidents/recent?limit=N`
- `GET /incidents/near?lat=&lng=&radius_mi=&days=` — Haversine radius search
- `GET /stats/overview` — counts (day/week/month/year), top_categories, top_districts, wow_change
- `GET /neighborhoods` and `GET /neighborhoods/{slug}`
- `GET /categories` and `GET /categories/{slug}`
- `GET /wicked-picks?limit=N`
- `GET /images/plates` — list of self-hosted Boston imagery for rotating plate
- `GET /geocode?q=...` — OSM Nominatim proxy, Boston-biased

## Frontend Routes
- `/` Home — masthead + hamburger nav, ticker, hero w/ address quick-search + rotating Boston imagery, stats, hero map, blotter, Wicked Picks, neighborhood grid, category grid
- `/map` — full interactive map + address lookup card with radius (1/10–1mi) + "Reading on" results panel + filter bar (days/category/neighborhood)
- `/neighborhoods` and `/neighborhoods/:slug`
- `/categories/:slug`
- `/wicked-picks` — editorial column with rotating plate
- `/about`

## Voice Rules
- Dry, observational, never punching down
- Targets: unlocked doors, vague suspect descriptions, leaving cars running, package theft, parking
- Off-limits: victims, neighborhoods, communities, BPD investigators
- Homicide / shooting commentary explicitly restrained

## Implemented Timeline
**May 15 (initial)**
- Backend: 10 endpoints, MongoDB caching, 7,795 real BPD incidents
- Frontend: 7 routes, masthead, ticker, dark CartoDB map w/ clustered colored dots, 19 neighborhoods, 10 categories, Wicked Picks
- Testing: 17/17 backend + 7/7 routes verified

**May 15 (iteration 1 — imagery + pins)**
- Self-hosted 4 Boston images served from `/api/static/images/` (Fenway, Beacon Hill, Zakim, Harbor)
- RotatingPlate component with 7s crossfade + manual dots
- Modern SpotCrime-inspired SVG pushpin markers (40x52 teardrop body, cream face, ink-black glyph per category) — 3x bigger than original dots
- Removed mix-blend-mode that was killing dark images

**May 15 (iteration 2 — address search)**
- OSM Nominatim geocoding with Boston viewbox + 30d Mongo cache
- `/api/incidents/near` Haversine radius search w/ category breakdown
- AddressSearch component with input, radius selector, results panel, error states
- Amber star pin + dashed amber radius circle on map
- Homepage hero quick-search → deep-link to /map?address=...

**May 15 (iteration 3 — mobile-first + iOS fix)**
- Responsive headlines (text-4xl mobile → text-7xl desktop)
- Hamburger menu drawer on phones (sm:hidden)
- Map gesture handling — two fingers to pan, Ctrl/Cmd+scroll to zoom (page scrolls past map normally on touch)
- Responsive map heights (55-60vh mobile, 480-640px desktop)
- Collapsible legend (`<details>`)
- Suppressed cross-origin "Script error." events in index.html so iOS Safari doesn't show meaningless dev overlay
- Added ErrorBoundary component as graceful fallback
- Proper viewport meta (`viewport-fit=cover`), apple-mobile-web-app meta tags

## Data Caveats
- BPD's CKAN feed typically lags 2–3 weeks behind real time. "Last 24h" / "Last 7d" counts may legitimately read 0; Wicked Picks deliberately uses 30-day window.
- Records can be revised by BPD; cache replaces wholesale on refresh.

## Backlog
**P1**
- Email alerts (SendGrid/Resend) — neighborhood subscriptions
- Time-series chart for stats by category over 90d
- Map heatmap toggle (leaflet.heat)
- Background scheduler for cache refresh (instead of per-request check)
- OG share cards for Wicked Picks (server-side image gen)

**P2**
- "Most Wanted" page (BPD wanted feed if available)
- Neighborhood comparison tool
- Embeddable widget (single-iframe map)
- Mobile-first bottom-sheet filter UI for the map page
- RSS feed for Wicked Picks
- Reverse-geocode "what's near me" using geolocation API
