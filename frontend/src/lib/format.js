// Color codes for the 10 crime categories. Restrained palette, civic.
export const CATEGORY_COLORS = {
    homicide: "#5a0a0a",
    shooting: "#8b1c1c",
    robbery: "#a62121",
    assault: "#c14a23",
    burglary: "#14253a",
    larceny: "#2c4a6e",
    vehicle_theft: "#3d6996",
    vandalism: "#5b7ba0",
    drugs: "#d9772b",
    other: "#66635c",
};

export const CATEGORY_ORDER = [
    "homicide",
    "shooting",
    "robbery",
    "assault",
    "burglary",
    "larceny",
    "vehicle_theft",
    "vandalism",
    "drugs",
    "other",
];

export const CATEGORY_LABELS = {
    homicide: "Homicide",
    shooting: "Shooting",
    robbery: "Robbery",
    assault: "Assault",
    burglary: "Burglary",
    larceny: "Larceny / Theft",
    vehicle_theft: "Vehicle Theft",
    vandalism: "Vandalism",
    drugs: "Drugs",
    other: "Other",
};

export const CATEGORY_SLUGS = {
    homicide: "homicide",
    shooting: "shooting",
    robbery: "robbery",
    assault: "assault",
    burglary: "burglary",
    larceny: "larceny",
    vehicle_theft: "vehicle-theft",
    vandalism: "vandalism",
    drugs: "drugs",
    other: "other",
};

export const colorFor = (key) => CATEGORY_COLORS[key] || CATEGORY_COLORS.other;

// Format an ISO timestamp into "Mon, May 12 · 8:42 PM"
export const formatWhen = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });
};

export const formatRelative = (iso) => {
    if (!iso) return "Recently";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "Recently";
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return mins <= 1 ? "Just now" : `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

export const TICKER_MESSAGES = [
    "WICKED DRY DESK",
    "BOSTON PD OPEN DATA",
    "TRIPLE-DECKER SAFETY HOURS: ALWAYS",
    "LOCK THE BACK DOOR, HON",
    "PARK SO YOU CAN GET OUT",
    "THE T IS RUNNING, ALLEGEDLY",
    "PACKAGE THEFT IS UP — IT'S ALWAYS UP",
    "TAKE THE DASH CAM INSIDE",
    "MASSHOLES OPERATE WITH CARE",
    "PATRIOT'S DAY MAKES EVERYONE WEIRD",
    "DUNKIN' AT 5 AM, PD AT 5:15",
    "WALK FACING TRAFFIC",
    "FENWAY IS A NEIGHBORHOOD, NOT JUST A PARK",
    "SOUTHIE PARKING IS A CONTACT SPORT",
];
