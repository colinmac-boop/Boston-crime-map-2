import { Link } from "react-router-dom";

export default function Footer() {
    return (
        <footer className="mt-20 border-t-2 border-[var(--ink)] bg-[var(--surface-dark)] text-[var(--bg)]" data-testid="footer">
            <div className="max-w-7xl mx-auto px-5 py-12 grid md:grid-cols-3 gap-10">
                <div>
                    <div className="kicker text-[var(--amber)]">Colophon</div>
                    <p className="font-display text-2xl leading-tight mt-2">
                        The Boston Crime Map
                    </p>
                    <p className="font-body text-sm text-neutral-300 mt-3 leading-relaxed">
                        An independent civic-data publication.
                        Incident records sourced from the Boston Police Department's public open-data feed.
                        Editorial commentary is opinionated, observational, and intentionally dry.
                    </p>
                </div>
                <div>
                    <div className="kicker text-[var(--amber)]">Sections</div>
                    <ul className="mt-3 space-y-1.5 font-sub uppercase text-sm tracking-widest">
                        <li><Link to="/map" className="hover:text-[var(--amber)]">Interactive Crime Map</Link></li>
                        <li><Link to="/neighborhoods" className="hover:text-[var(--amber)]">All Neighborhoods</Link></li>
                        <li><Link to="/wicked-picks" className="hover:text-[var(--amber)]">Wicked Picks</Link></li>
                        <li><Link to="/about" className="hover:text-[var(--amber)]">About &amp; Data Sources</Link></li>
                    </ul>
                </div>
                <div>
                    <div className="kicker text-[var(--amber)]">Disclaimer</div>
                    <p className="font-body text-sm text-neutral-300 mt-3 leading-relaxed">
                        Data is published by BPD and modified for display.
                        No warranties as to completeness or accuracy.
                        Incidents reflect <em>reports</em> — not convictions.
                        In a real emergency, call 911. For non-emergencies, call (617) 343-4200.
                    </p>
                </div>
            </div>
            <div className="border-t border-neutral-800">
                <div className="max-w-7xl mx-auto px-5 py-4 text-xs font-mono text-neutral-500 flex justify-between flex-wrap gap-2">
                    <span>© {new Date().getFullYear()} The Wicked Dry Desk</span>
                    <span>Made with brick, Dunkin', and a long memory.</span>
                </div>
            </div>
        </footer>
    );
}
