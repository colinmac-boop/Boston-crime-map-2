import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";

const NAV = [
    { to: "/", label: "Front Page", end: true },
    { to: "/map", label: "Crime Map" },
    { to: "/neighborhoods", label: "Neighborhoods" },
    { to: "/wicked-picks", label: "Wicked Picks" },
    { to: "/about", label: "About / Data" },
];

const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
});

const todayShort = new Date().toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
});

const volume = `Vol. I · No. ${Math.max(1, Math.floor((Date.now() - new Date("2026-05-01").getTime()) / 86400000) + 1)}`;

export default function Masthead() {
    const [open, setOpen] = useState(false);
    const { pathname } = useLocation();

    // Close mobile menu on route change
    useEffect(() => { setOpen(false); }, [pathname]);

    return (
        <header className="border-b-2 border-[var(--ink)]" data-testid="masthead">
            {/* Top strap with date and volume */}
            <div className="bg-[var(--ink)] text-[var(--bg)]">
                <div className="max-w-7xl mx-auto px-4 sm:px-5 py-1.5 sm:py-2 flex items-center justify-between text-[10px] sm:text-[11px] font-mono tracking-widest uppercase gap-2">
                    <span data-testid="masthead-volume" className="truncate">{volume}</span>
                    <span className="hidden md:inline">Boston, Massachusetts · 02108</span>
                    <span data-testid="masthead-date" className="truncate text-right">
                        <span className="hidden sm:inline">{today}</span>
                        <span className="sm:hidden">{todayShort}</span>
                    </span>
                </div>
            </div>

            {/* Main masthead with mobile menu button */}
            <div className="max-w-7xl mx-auto px-4 sm:px-5 pt-5 sm:pt-8 pb-3 sm:pb-4 relative">
                <div className="flex items-start justify-between gap-3">
                    <Link to="/" className="block flex-1 min-w-0" data-testid="masthead-logo">
                        <div className="kicker mb-1 text-[10px] sm:text-[11px]">The Wicked Dry Desk · est. now</div>
                        <h1 className="masthead-name text-[2.2rem] xs:text-[2.6rem] sm:text-6xl md:text-7xl lg:text-8xl">
                            The <span className="italic" style={{ color: "var(--oxblood)" }}>Boston</span><br />
                            Crime Map
                        </h1>
                    </Link>
                    <div className="hidden lg:block text-right max-w-xs shrink-0">
                        <p className="font-display italic text-base lg:text-lg leading-snug">
                            Real BPD blotter data. Twenty-three districts. One opinionated voice from the back of the room.
                        </p>
                    </div>
                    {/* Mobile menu toggle */}
                    <button
                        onClick={() => setOpen((o) => !o)}
                        className="sm:hidden shrink-0 mt-1 p-2 border-2 border-[var(--ink)] bg-[var(--bg)] hover:bg-[var(--ink)] hover:text-[var(--bg)] transition-colors"
                        aria-label={open ? "Close menu" : "Open menu"}
                        aria-expanded={open}
                        data-testid="nav-toggle"
                    >
                        {open ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>
            </div>

            {/* Nav rule */}
            <div className="rule-double max-w-7xl mx-auto" />

            {/* Desktop nav (always visible on sm+) */}
            <nav
                className="hidden sm:flex max-w-7xl mx-auto px-5 py-2.5 sm:py-3 items-center gap-4 sm:gap-6 flex-wrap"
                data-testid="primary-nav"
            >
                {NAV.map((item) => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.end}
                        data-testid={`nav-${item.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                        className={({ isActive }) =>
                            `font-sub uppercase tracking-widest text-sm transition-colors ${
                                isActive
                                    ? "text-[var(--oxblood)] font-semibold underline underline-offset-[6px] decoration-2"
                                    : "text-[var(--ink)] hover:text-[var(--oxblood)]"
                            }`
                        }
                    >
                        {item.label}
                    </NavLink>
                ))}
            </nav>

            {/* Mobile nav drawer */}
            <nav
                className={`sm:hidden overflow-hidden transition-[max-height] duration-300 ease-out ${
                    open ? "max-h-96" : "max-h-0"
                }`}
                data-testid="mobile-nav"
            >
                <ul className="px-4 py-2 flex flex-col">
                    {NAV.map((item) => (
                        <li key={item.to}>
                            <NavLink
                                to={item.to}
                                end={item.end}
                                data-testid={`mobile-nav-${item.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                                className={({ isActive }) =>
                                    `block py-2.5 font-sub uppercase tracking-widest text-base border-b border-[var(--ink)]/30 ${
                                        isActive
                                            ? "text-[var(--oxblood)] font-semibold"
                                            : "text-[var(--ink)]"
                                    }`
                                }
                            >
                                {item.label}
                            </NavLink>
                        </li>
                    ))}
                </ul>
            </nav>
            <div className="rule max-w-7xl mx-auto" />
        </header>
    );
}
