"""Site copy — the real, human-authored words. Brand voice: a trusted reference
desk, calm and nonpartisan. Kept in one place so tone stays consistent."""
from __future__ import annotations

BRAND = "Plumbline"
TAGLINE = "Every 2026 election date — and the deadlines that come first."

HOME_HERO = {
    "eyebrow": "2026 midterms · 50 states + DC",
    "h1": "Your next election, and every deadline before it.",
    "subhead": (
        "Pick your state to see every 2026 election date — plus the registration "
        "and early-voting deadlines that close weeks earlier. Every date links to "
        "the election office it came from."
    ),
    # Rendered inside <noscript> under the state select.
    "nojs": "Or scroll down to the A–Z list of states.",
}

# Inline, directly under the deadline rail on state hubs and detail pages — where
# someone is deciding whether they still have time, not buried in the footer.
CONFIRM_NOTE = (
    "Deadlines move. Confirm with your election office before you rely on a date — "
    "this record links to theirs."
)

# Shown when an upcoming election's registration deadline has already passed.
REG_CLOSED_NOTE = (
    "Voter registration for this election closed on {date}. Some states still allow "
    "you to register in person or on election day — your election office has the "
    "final word."
)

BALLOT_INTRO = (
    "What you'll be voting on. Offices are listed as the state publishes them; your "
    "own ballot also carries local races and any measures for your address."
)

REMIND_INTRO = (
    "We can't email you — Plumbline has no accounts and collects nothing about you. "
    "What we can do is hand your calendar the dates. Add the file below and your "
    "phone will remind you before each deadline, the same way it reminds you of "
    "anything else."
)

FAQ_PAGE = [
    ("When is the 2026 general election?",
     "Tuesday, November 3, 2026, nationwide. Most states also hold a primary earlier "
     "in the year, and some hold a runoff after it. Your state's page lists every "
     "date that's left."),
    ("How do I register to vote?",
     "Registration is run by your state, and the rules differ in every one — the "
     "deadline, whether you can register online, and whether you can still register "
     "on election day. Your state's page shows the registration deadline for each "
     "election and links to the office that handles it. Start there; it's the only "
     "source that can actually register you."),
    ("What's on my ballot?",
     "Every election page lists the offices the state has published — U.S. Senate, "
     "governor, U.S. House, statewide offices, the legislature. Your own ballot also "
     "carries local races and any ballot measures for your address, which only your "
     "county or city election office can show you."),
    ("I missed my registration deadline. Is it over?",
     "Not necessarily. A number of states allow registration in person, or on "
     "election day itself. We don't publish those rules because they vary by state "
     "and change — check with your election office before you assume you're out."),
    ("Where do these dates come from?",
     "Each one is taken from an official election-authority page, recorded with the "
     "link and the date we retrieved it, and checked by a person before it's "
     "published. Every record on the site shows its source; you can open it and see "
     "for yourself."),
    ("A date here looks wrong. What do I do?",
     "Tell us and we'll check it. Every correction is logged and dated. If it's "
     "urgent — an election is close — trust your election office over us and let us "
     "fix the record afterwards."),
]

WHY_DATES_GET_MISSED = [
    "Everyone knows there's an election in November 2026. Far fewer people could "
    "name the date of their state's primary, the runoff that follows it, or the "
    "registration deadline that quietly closes weeks earlier. A midterm year is a "
    "chain of dates, and the big one at the end is the only link anyone marks.",
    "The rest of the chain is where votes are actually won and lost: primaries "
    "that decide most seats before November, runoffs scheduled on short notice, "
    "special elections for seats left open mid-term, and the registration, "
    "mail-ballot, and early-voting windows that close before each of them. Miss "
    "one deadline and the election is over for you before it starts.",
    "That's the gap Plumbline exists to close. We track every statewide primary, "
    "runoff, and general in the 2026 cycle — and the special, municipal, and "
    "off-cycle elections around it — with the key dates and deadlines for each, "
    "kept current and clearly sourced.",
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
    "Dates change. Always confirm with your official state or local election "
    "office before you rely on one — every record here links straight to theirs. "
    "Plumbline is an independent, nonpartisan reference for U.S. election dates "
    "and deadlines, not affiliated with any government agency, political party, "
    "or campaign."
)

# Replaces the three-chip legend when only one confidence tier exists in the data.
# Advertising "some of our dates are inferred" to a first-time visitor teaches
# doubt that the current dataset does not warrant.
FOOTER_LEGEND_SOLO = (
    "Every date on this site is confirmed against an official election-office page."
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
    ("official", "From official election offices"),
    ("verified", "Checked by a person"),
    ("nonpartisan", "Independent and nonpartisan"),
    ("versioned", "Every change is logged"),
]

CTA = {
    "find_state": "Show my dates",
    "browse_states": "Browse all states",
    "view_source": "View the official page",
    # The .ics file IS the reminder product — sell the benefit, not the format.
    "add_to_calendar": "Add to my calendar — get a reminder",
    "subscribe_ics": "Add these dates to my calendar",
    "read_methodology": "How we check every date",
    "how_we_verify": "How we check dates",
    "get_data_access": "Get data access",
    "report_correction": "Report a correction",
    "toggle_theme": "Switch theme",
    "skip_to_content": "Skip to content",
}
