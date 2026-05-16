export default function AboutPage() {
    return (
        <main className="max-w-4xl mx-auto px-5 pt-8 pb-10" data-testid="about-page">
            <div className="kicker">Section · About</div>
            <h2 className="headline-xl text-4xl sm:text-5xl md:text-7xl mt-1">About this paper</h2>

            <section className="mt-8 editorial-card p-6 md:p-8">
                <p className="font-display text-xl md:text-2xl leading-snug dropcap">
                    The Boston Crime Map is an independent civic-data publication. It pairs real incident reports from the Boston Police Department's public open-data feed with a dry, deadpan editorial voice. The data is real. The opinions are ours. We try not to be wrong about either.
                </p>
            </section>

            <section className="mt-10">
                <div className="rule mb-3" />
                <div className="kicker">Where the data comes from</div>
                <h3 className="headline-lg text-3xl mt-1">Boston Police Department · Open Data</h3>
                <p className="font-body text-base leading-relaxed mt-3">
                    All incidents on this site come from{" "}
                    <a
                        href="https://data.boston.gov/dataset/crime-incident-reports-august-2015-to-date-source-new-system"
                        className="underline decoration-2 underline-offset-2 hover:text-[var(--oxblood)]"
                        target="_blank"
                        rel="noreferrer"
                    >
                        Crime Incident Reports (August 2015 – Present), Boston Police Department
                    </a>
                    , published on Analyze Boston. We pull the most recent reports, cache them, and refresh on the hour. Records are subject to revision by BPD as cases develop. Data is provided under the Open Data Commons Public Domain Dedication.
                </p>
            </section>

            <section className="mt-10">
                <div className="rule mb-3" />
                <div className="kicker">How we group categories</div>
                <p className="font-body text-base leading-relaxed mt-3">
                    BPD's offense descriptions are detailed and inconsistent. We map them into ten plain-language buckets — Homicide, Shooting, Robbery, Assault, Burglary, Larceny, Vehicle Theft, Vandalism, Drugs, Other — using simple keyword rules. We surface the raw description on every incident so you can verify.
                </p>
            </section>

            <section className="mt-10">
                <div className="rule mb-3" />
                <div className="kicker">A note on tone</div>
                <p className="font-body text-base leading-relaxed mt-3">
                    The commentary here is dry, observational, and Boston. It is never aimed at victims, at neighborhoods, or at the people doing the police work. The targets — to the extent there are any — are unlocked back doors, vague suspect descriptions, and the universal habit of leaving your car running with the keys in it.
                </p>
            </section>

            <section className="mt-10">
                <div className="rule mb-3" />
                <div className="kicker">Disclaimer</div>
                <p className="font-body text-base leading-relaxed mt-3">
                    Reported incidents are not convictions. Suspect descriptions, locations, and times reflect BPD records and may be revised. This site does not display personally-identifying information. For emergencies, call 911. For Boston Police non-emergency, call (617) 343-4200.
                </p>
            </section>

            <section className="mt-10">
                <div className="rule mb-3" />
                <div className="kicker">Further reference</div>
                <ul className="mt-3 font-sub uppercase tracking-widest text-sm space-y-1.5">
                    <li>
                        <a className="underline hover:text-[var(--oxblood)]" target="_blank" rel="noreferrer" href="https://police.boston.gov/">
                            Boston Police Department →
                        </a>
                    </li>
                    <li>
                        <a className="underline hover:text-[var(--oxblood)]" target="_blank" rel="noreferrer" href="https://data.boston.gov/group/public-safety">
                            Analyze Boston · Public Safety datasets →
                        </a>
                    </li>
                    <li>
                        <a className="underline hover:text-[var(--oxblood)]" target="_blank" rel="noreferrer" href="https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend">
                            FBI Crime Data Explorer · MA →
                        </a>
                    </li>
                </ul>
            </section>
        </main>
    );
}
