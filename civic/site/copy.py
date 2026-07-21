"""Site copy — the real, human-authored words. Brand voice: a trusted reference
desk, calm and nonpartisan. Kept in one place so tone stays consistent."""
from __future__ import annotations

BRAND = "Plumbline"
TAGLINE = "Verified dates for the elections between the elections."

HOME_HERO = {
    "eyebrow": "Off-cycle & local elections, United States",
    "h1": "Know when your next election really is.",
    "subhead": (
        "Plumbline is a verified, continuously sourced calendar of off-cycle and "
        "local elections — the primaries, runoffs, municipal races, school-board "
        "seats, and ballot measures that decide the most and get announced the "
        "least. Every date shows its source, its confidence level, and the day we "
        "last checked it."
    ),
}

WHAT_IS_OFF_CYCLE = [
    "Most people know the big November elections — the ones with a president or a "
    "governor at the top of the ticket. An off-cycle election is nearly everything "
    "else: a race, runoff, or ballot measure held on some other date. Many land in "
    "odd-numbered years, in spring or summer, or on a Tuesday that isn't on anyone's "
    "radar.",
    "These are the elections that fill your city council and school board, pass or "
    "reject local bond measures, recall officials, and fill seats left open "
    "mid-term. Turnout is often a fraction of a presidential year, which means each "
    "vote carries more weight — and the deadlines to register, request a mail "
    "ballot, or vote early usually arrive weeks before a date almost no one has "
    "marked.",
    "That's the gap Plumbline exists to close. We track off-cycle primaries, general "
    "and special elections, municipal and school-board races, runoffs, and ballot "
    "measures across states, counties, cities, and special districts — with the key "
    "dates and deadlines for each, kept current and clearly sourced.",
]

ABOUT = [
    "Plumbline is a curation-first calendar. Almost anyone can scrape a list of "
    "dates; the hard part — the entire product, really — is being right, and being "
    "able to show why.",
    "Every record starts from a source, not a guess. We work from official "
    "election-authority pages first: secretaries of state, county clerks, and city "
    "and district election offices. Where an official date isn't published yet, we "
    "may record one from a credible secondary source or infer it from statute and "
    "past schedule — and we label it as exactly that.",
    "Alongside confidence, every record keeps its provenance: the source link, the "
    "date we retrieved it, who verified it, and when. A record isn't published or "
    "exported until a person has verified it. And once a date is verified, it is "
    "never silently overwritten — if a later source disagrees, the change is held "
    "for human review rather than quietly replacing a confirmed value. Corrections "
    "are deliberate, logged, and reversible.",
    "The name is the promise. A plumb line is the oldest tool for finding true — a "
    "weight on a string that shows you exactly where level is, no matter what's "
    "leaning around it. That's the job here: a steady, checkable reference for dates "
    "that are otherwise scattered, provisional, or wrong.",
    "We're independent and nonpartisan. We don't run campaigns, take positions, or "
    "tell anyone how to vote. And we're candid about our limits: election dates and "
    "deadlines change, and the official word always belongs to your local election "
    "office. Found something off? Tell us — every correction makes the record "
    "stronger.",
]

METHODOLOGY_INTRO = "In short: we source, tier, verify, protect, and version."

METHODOLOGY_STEPS = [
    ("Source", "We start from official election-authority pages wherever they "
     "exist, and record the source link and the date we retrieved it."),
    ("Tier by confidence", "Every date is labeled official, secondary, or inferred, "
     "so you always know how firm it is."),
    ("Verify", "A person checks a record before it's published or exported; "
     "unverified records stay in staging."),
    ("Protect verified data", "A confirmed date is never silently overwritten — "
     "conflicting updates are queued for human review, then applied or rejected on "
     "the record."),
    ("Version", "Data ships as dated, immutable releases (YYYY.MM.DD) with a "
     "changelog, so every correction is transparent and traceable."),
]

METHODOLOGY_OUTRO = (
    "When in doubt, confirm with your local election office — they have the last "
    "word."
)

DATA_PRODUCT = [
    "Plumbline Data is the same verified record set, packaged as versioned flat "
    "files you can drop straight into a model, a CRM, or a field plan.",
    "Every release is a plain CSV stamped with a calendar version (YYYY.MM.DD) and "
    "paired with a human-readable changelog. Because versions are immutable and "
    "every change is logged, you can diff any two releases and see exactly what "
    "moved — a new special election, a shifted registration deadline, a date "
    "promoted from inferred to official. No silent edits, no guessing what changed "
    "since last week.",
    "Each row carries what you need to trust it and to join it: a stable, "
    "deterministic ID that always maps to the same real-world election; the "
    "jurisdiction and offices; the election date and the deadlines around it — "
    "voter registration, mail-ballot request, the early-voting window, and "
    "candidate filing; the source URL and retrieval date; the confidence level; and "
    "the verification status. Time zones are explicit. The same data is available "
    "as JSON, and as per-jurisdiction ICS calendar feeds.",
]

DATA_PRODUCT_AUDIENCES = [
    ("PACs & advocacy groups", "Time field programs, mail, and ad buys to real "
     "deadlines across many jurisdictions at once."),
    ("Prediction & information markets", "A documented, versioned reference for when "
     "a contest occurs — and how firm that date is."),
    ("Newsrooms, researchers & civic tools", "Provenance you can cite and a "
     "changelog you can audit."),
]

DATA_PRODUCT_CLOSER = (
    "You get the dates, the deadlines, and — just as important — the receipts."
)

FOOTER_BLURB = (
    "Plumbline is an independent, nonpartisan reference for off-cycle and local "
    "election dates and deadlines across the United States. Every date is sourced, "
    "confidence-rated, and human-verified — but dates change, so always confirm "
    "with your official local election office before you rely on one. Not "
    "affiliated with any government agency, political party, or campaign."
)

# aria-label, when present, MUST begin with the visible link text so it satisfies
# WCAG 2.5.3 Label in Name (voice control "click States" works).
NAV = [
    ("States", "/states/", "States — browse elections by state"),
    ("Methodology", "/methodology/", "Methodology — how we source and verify dates"),
    ("Data", "/data/", "Data — bulk exports for teams and developers"),
    ("About", "/about/", None),
]

FOOTER_COLUMNS = [
    ("Elections", [
        ("Browse all states", "/states/"),
        ("How we verify dates", "/methodology/"),
    ]),
    ("Project", [
        ("About Plumbline", "/about/"),
        ("Methodology", "/methodology/"),
        ("Data & exports", "/data/"),
    ]),
    ("Developers & data", [
        ("Data product overview", "/data/"),
        ("Calendar feeds (.ics)", "/data/#calendar-feeds"),
    ]),
    ("Site", [
        ("Sitemap", "/sitemap.xml"),
        ("Accessibility statement", "/about/#accessibility"),
    ]),
]

# Above-the-fold trust bar: (icon key, label). Quieter than the CTA.
TRUST_BAR = [
    ("official", "Cites an official source"),
    ("verified", "Human-verified"),
    ("nonpartisan", "Independent & nonpartisan"),
    ("versioned", "Versioned & auditable"),
]

CTA = {
    "find_state": "Find your state",
    "browse_states": "Browse all states",
    "view_source": "View source",
    "add_to_calendar": "Add to calendar (.ics)",
    "subscribe_ics": "Subscribe to this calendar",
    "read_methodology": "Read the methodology",
    "how_we_verify": "How we verify",
    "get_data_access": "Get data access",
    "report_correction": "Report a correction",
    "toggle_theme": "Switch theme",
    "skip_to_content": "Skip to content",
}
