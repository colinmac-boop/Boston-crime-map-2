"""Static metadata: Boston neighborhoods, crime categories, dry editorial copy.

This is the editorial backbone. Districts → neighborhoods is approximate (some
neighborhoods span multiple districts), but it's good enough for filtering.
"""
from __future__ import annotations

NEIGHBORHOODS = [
    {
        "slug": "south-boston",
        "name": "South Boston",
        "districts": ["C6"],
        "tagline": "Triple-deckers, the beach, and an opinion on every parking spot.",
        "blurb": (
            "Southie. The waterfront half is now glass condos; the rest still "
            "looks like 1978 if you squint. Property crime is mostly cars and "
            "front porches around L Street and the Broadway corridor."
        ),
    },
    {
        "slug": "dorchester",
        "name": "Dorchester",
        "districts": ["C11", "B3"],
        "tagline": "Bigger than most cities. Acts like a small town.",
        "blurb": (
            "OFD or you don't get it. Dorchester runs from Adams Village to "
            "Codman Square to Fields Corner. Watch for break-ins on the side "
            "streets and the occasional weekend nonsense near the Avenue."
        ),
    },
    {
        "slug": "roxbury",
        "name": "Roxbury",
        "districts": ["B2"],
        "tagline": "Old Boston. Real Boston. Don't let anyone tell you otherwise.",
        "blurb": (
            "Dudley — sorry, Nubian — Square is the heart. Real numbers, "
            "real history, real neighbors. Reads worse on a map than it lives "
            "in person, which is the whole point of looking at the map."
        ),
    },
    {
        "slug": "jamaica-plain",
        "name": "Jamaica Plain",
        "districts": ["E13"],
        "tagline": "Pond walks, three-deckers, and a tote bag minimum.",
        "blurb": (
            "JP. Centre Street is the spine. Crime here is mostly property "
            "and the occasional dispute over whose dog started it."
        ),
    },
    {
        "slug": "back-bay",
        "name": "Back Bay",
        "districts": ["D4"],
        "tagline": "Brownstones. Brunch. Bicycle theft.",
        "blurb": (
            "Newbury, Boylston, Comm Ave. Larceny is the headline — bikes, "
            "phones, packages off stoops. It is what it is."
        ),
    },
    {
        "slug": "fenway",
        "name": "Fenway / Kenmore",
        "districts": ["D4"],
        "tagline": "Citgo sign, students, and the world's largest beer line.",
        "blurb": (
            "Game-day spikes are real. Off-season it's mostly student "
            "apartments and the occasional confused tourist looking for "
            "Cheers in the wrong neighborhood."
        ),
    },
    {
        "slug": "north-end",
        "name": "North End",
        "districts": ["A1"],
        "tagline": "Cannoli, double-parking, and zero square footage.",
        "blurb": (
            "Hanover Street is the heart. Property crime is low; the real "
            "danger is ordering the wrong thing at the wrong place."
        ),
    },
    {
        "slug": "beacon-hill",
        "name": "Beacon Hill",
        "districts": ["A1"],
        "tagline": "Gas lamps. Cobblestones. Surprisingly steep.",
        "blurb": (
            "Charles Street, the State House, the flat. Pickpocketing on the "
            "Common nearby is the usual story; the Hill itself stays quiet."
        ),
    },
    {
        "slug": "downtown",
        "name": "Downtown / Financial District",
        "districts": ["A1"],
        "tagline": "Suits by day. Cleaning crews by night.",
        "blurb": (
            "Around DTX and the FiDi: shoplifting, the occasional commuter-"
            "rail dispute, and a lot of incidents that aren't really crimes "
            "so much as the city being the city."
        ),
    },
    {
        "slug": "chinatown",
        "name": "Chinatown",
        "districts": ["A1"],
        "tagline": "Dim sum at 1 AM. The good kind of chaos.",
        "blurb": (
            "Small geographically, big in foot traffic. Larceny and the "
            "occasional fight outside a karaoke spot. Eat, leave, repeat."
        ),
    },
    {
        "slug": "south-end",
        "name": "South End",
        "districts": ["D4", "C6"],
        "tagline": "Bow-front brownstones and a brunch waitlist.",
        "blurb": (
            "Tremont, Washington, the Square. Mostly property crime. The "
            "vibes shift hard depending on which block you're on."
        ),
    },
    {
        "slug": "allston-brighton",
        "name": "Allston / Brighton",
        "districts": ["D14"],
        "tagline": "September 1st is its own holiday and its own crime spree.",
        "blurb": (
            "Student turnover. Couches on curbs. Bike theft, package theft, "
            "and the slow-motion comedy of move-out day. The food is great."
        ),
    },
    {
        "slug": "east-boston",
        "name": "East Boston",
        "districts": ["A7"],
        "tagline": "The skyline view nobody mentions until it gets expensive.",
        "blurb": (
            "Eagle Hill, Maverick, Day Square. Quietly changing fast. Crime "
            "trends look more like a neighborhood than a punchline."
        ),
    },
    {
        "slug": "charlestown",
        "name": "Charlestown",
        "districts": ["A15"],
        "tagline": "Bunker Hill, the Navy Yard, and a long memory.",
        "blurb": (
            "Townie or transplant, you'll get strong opinions about both. "
            "Property crime is the bulk of it; the rest is parking."
        ),
    },
    {
        "slug": "mattapan",
        "name": "Mattapan",
        "districts": ["B3"],
        "tagline": "Trolley town. Underrated, over-stereotyped.",
        "blurb": (
            "Blue Hill Ave runs through it. The numbers tell one story, the "
            "porch on Blue Ledge Drive tells another. Use both."
        ),
    },
    {
        "slug": "hyde-park",
        "name": "Hyde Park",
        "districts": ["E18"],
        "tagline": "Last stop on the commuter rail. First stop on the cookout list.",
        "blurb": (
            "Cleary Square, Readville, Fairmount. Mostly residential, mostly "
            "quiet, occasionally lively at the wrong intersection."
        ),
    },
    {
        "slug": "west-roxbury",
        "name": "West Roxbury / Roslindale",
        "districts": ["E5"],
        "tagline": "Lawns. Garages. The peace you moved out for.",
        "blurb": (
            "Centre Street in Roslindale Village is the social hub. Crime "
            "here looks like the suburbs because functionally it is."
        ),
    },
    {
        "slug": "mission-hill",
        "name": "Mission Hill",
        "districts": ["B2"],
        "tagline": "Hospitals, students, and Mission Main.",
        "blurb": (
            "Tremont, Huntington, the Hill itself. Theft from autos near "
            "the medical district is a perennial. Take the dash cam in."
        ),
    },
    {
        "slug": "seaport",
        "name": "Seaport / Fort Point",
        "districts": ["C6", "A1"],
        "tagline": "Glass, wind, and an open table on a Tuesday.",
        "blurb": (
            "The newest neighborhood by a century. Mostly thefts from "
            "construction sites and the occasional rooftop-bar incident."
        ),
    },
]


CATEGORIES = [
    {
        "slug": "assault",
        "key": "assault",
        "label": "Assault",
        "bucket": "violent",
        "definition": (
            "A physical attack or credible threat of attack against a person. "
            "Aggravated assault involves a weapon or serious injury; simple "
            "assault does not."
        ),
        "boston_note": (
            "Reported assaults are the broadest violent-crime category. "
            "Domestic and bar-related incidents make up a large share."
        ),
    },
    {
        "slug": "robbery",
        "key": "robbery",
        "label": "Robbery",
        "bucket": "violent",
        "definition": (
            "Taking property directly from a person using force, threat, or "
            "intimidation. Different from larceny (no contact) and burglary "
            "(no person present)."
        ),
        "boston_note": (
            "Street robberies tend to cluster around transit stops at night. "
            "Phones are the headline item."
        ),
    },
    {
        "slug": "shooting",
        "key": "shooting",
        "label": "Shooting",
        "bucket": "violent",
        "definition": (
            "An incident involving discharge of a firearm — whether or not "
            "anyone was struck. Includes drive-by shootings and confirmed "
            "shots-fired calls."
        ),
        "boston_note": (
            "BPD flags shooting incidents in a dedicated field. Most are "
            "concentrated in a handful of districts."
        ),
    },
    {
        "slug": "homicide",
        "key": "homicide",
        "label": "Homicide",
        "bucket": "violent",
        "definition": (
            "The killing of one person by another. Includes murder and "
            "manslaughter. Excludes justified law-enforcement actions."
        ),
        "boston_note": (
            "Boston's homicide totals run low for a city its size. Each one "
            "still matters and gets dedicated detective work."
        ),
    },
    {
        "slug": "burglary",
        "key": "burglary",
        "label": "Burglary",
        "bucket": "property",
        "definition": (
            "Entering a building or structure unlawfully to commit a crime — "
            "usually theft. The defining element is the unlawful entry."
        ),
        "boston_note": (
            "Residential break-ins skew toward triple-decker side entries "
            "and unlocked back doors. Commercial break-ins skew toward "
            "small storefronts overnight."
        ),
    },
    {
        "slug": "larceny",
        "key": "larceny",
        "label": "Larceny / Theft",
        "bucket": "property",
        "definition": (
            "Taking property without force or threat — shoplifting, package "
            "theft, theft from a vehicle. Different from burglary (entering "
            "a building) and robbery (using force)."
        ),
        "boston_note": (
            "The single largest category by volume. Package theft, bike "
            "theft, and theft from autos drive the numbers."
        ),
    },
    {
        "slug": "vehicle-theft",
        "key": "vehicle_theft",
        "label": "Vehicle Theft",
        "bucket": "property",
        "definition": (
            "Stealing a motor vehicle, plus recoveries of stolen vehicles "
            "logged after the fact."
        ),
        "boston_note": (
            "Hyundai/Kia thefts spiked nationally; Boston caught the wave. "
            "Recoveries are often in the same district."
        ),
    },
    {
        "slug": "vandalism",
        "key": "vandalism",
        "label": "Vandalism",
        "bucket": "property",
        "definition": (
            "Intentional damage or defacement of property without taking "
            "it — graffiti, broken windows, slashed tires."
        ),
        "boston_note": (
            "Reports cluster around commercial corridors and high-traffic "
            "transit areas. Quality-of-life headline more than a safety one."
        ),
    },
    {
        "slug": "drugs",
        "key": "drugs",
        "label": "Drug Offenses",
        "bucket": "drugs",
        "definition": (
            "Possession, sale, manufacture, or distribution of controlled "
            "substances. Includes paraphernalia and trafficking charges."
        ),
        "boston_note": (
            "Reporting reflects enforcement priorities more than actual "
            "drug use. Trends shift with policy, not population."
        ),
    },
    {
        "slug": "other",
        "key": "other",
        "label": "Other",
        "bucket": "other",
        "definition": (
            "Incidents that don't fit the standard set — disturbances, "
            "weapon violations, traffic incidents, missing persons, and "
            "miscellaneous public-order calls."
        ),
        "boston_note": (
            "The catch-all. A lot of these are calls for service, not crimes."
        ),
    },
]

NEIGHBORHOOD_BY_SLUG = {n["slug"]: n for n in NEIGHBORHOODS}
CATEGORY_BY_SLUG = {c["slug"]: c for c in CATEGORIES}
CATEGORY_BY_KEY = {c["key"]: c for c in CATEGORIES}
