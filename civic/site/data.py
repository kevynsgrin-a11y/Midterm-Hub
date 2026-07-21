"""DB rows -> render-ready view models. Design-independent.

Everything the templates need is computed once here: human labels, formatted dates,
relative timing, clean URLs, and ordered deadline lists. Templates stay dumb.
"""
from __future__ import annotations

import datetime
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from ..exports import fetch_elections, row_to_record

# 50 states + DC. Full names for headings; URLs use the uppercase postal code
# (e.g. /states/VA/) — the same case the view models emit everywhere.
STATE_NAMES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

ELECTION_TYPE_LABELS: dict[str, str] = {
    "primary": "Primary",
    "general": "General",
    "runoff": "Runoff",
    "special": "Special",
    "municipal": "Municipal",
    "school_board": "School Board",
    "ballot_measure": "Ballot Measure",
}

JURISDICTION_TYPE_LABELS: dict[str, str] = {
    "state": "Statewide",
    "county": "County",
    "municipality": "Municipal",
    "school_district": "School District",
    "special_district": "Special District",
}

CONFIDENCE_LABELS: dict[str, str] = {
    "official": "Official source",
    "secondary": "Secondary source",
    "inferred": "Inferred",
}

CONFIDENCE_BLURB: dict[str, str] = {
    "official": "Confirmed against an official government source.",
    "secondary": "Sourced from a reputable secondary reference; pending official confirmation.",
    "inferred": "Inferred from statute or cycle patterns; treat as provisional.",
}


def fmt_full(d: datetime.date) -> str:
    """'Tuesday, May 4, 2027' — platform-independent (no %-d)."""
    return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}"


def fmt_short(d: datetime.date) -> str:
    """'May 4, 2027'."""
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def fmt_compact(d: datetime.date) -> str:
    """'May 4' — month + day only."""
    return f"{d.strftime('%b')} {d.day}"


def _parse(d: Optional[str]) -> Optional[datetime.date]:
    return datetime.date.fromisoformat(d) if d else None


@dataclass(frozen=True)
class Deadline:
    key: str
    label: str
    date: datetime.date
    formatted: str
    time: Optional[str] = None


@dataclass
class ElectionView:
    id: str
    state: str
    state_name: str
    jurisdiction_type: str
    jurisdiction_type_label: str
    jurisdiction_name: str
    jurisdiction_slug: str
    election_date: datetime.date
    election_type: str
    election_type_label: str
    offices: list[str]
    timezone: Optional[str]
    status: str
    confidence: str
    confidence_label: str
    confidence_blurb: str
    source_url: str
    source_retrieved_at: Optional[str]
    verified_by: Optional[str]
    verified_at: Optional[str]
    notes: Optional[str]
    deadlines: list[Deadline]
    _today: datetime.date
    # URL slug — equals jurisdiction_slug unless disambiguated for a same-slug,
    # different-type collision within the state (set during grouping).
    url_slug: str = ""

    @property
    def _slug(self) -> str:
        return self.url_slug or self.jurisdiction_slug

    @property
    def url(self) -> str:
        return f"/elections/{self.state}/{self._slug}/{self.id}/"

    @property
    def jurisdiction_url(self) -> str:
        return f"/elections/{self.state}/{self._slug}/"

    @property
    def state_url(self) -> str:
        return f"/states/{self.state}/"

    @property
    def title(self) -> str:
        return f"{self.jurisdiction_name} {self.election_type_label} Election"

    @property
    def date_full(self) -> str:
        return fmt_full(self.election_date)

    @property
    def date_short(self) -> str:
        return fmt_short(self.election_date)

    @property
    def date_iso(self) -> str:
        return self.election_date.isoformat()

    @property
    def days_until(self) -> int:
        return (self.election_date - self._today).days

    @property
    def is_upcoming(self) -> bool:
        return self.election_date >= self._today

    @property
    def countdown(self) -> str:
        n = self.days_until
        if n == 0:
            return "Today"
        if n == 1:
            return "Tomorrow"
        if n > 1:
            return f"in {n} days"
        if n == -1:
            return "yesterday"
        return f"{abs(n)} days ago"

    @property
    def offices_summary(self) -> str:
        return ", ".join(self.offices) if self.offices else ""


@dataclass
class JurisdictionView:
    state: str
    state_name: str
    slug: str
    name: str
    jurisdiction_type: str
    jurisdiction_type_label: str
    elections: list[ElectionView] = field(default_factory=list)
    # Disambiguated URL slug (see ElectionView.url_slug).
    url_slug: str = ""

    @property
    def _slug(self) -> str:
        return self.url_slug or self.slug

    @property
    def url(self) -> str:
        return f"/elections/{self.state}/{self._slug}/"

    @property
    def ics_filename(self) -> str:
        return f"{self.slug}.ics"

    @property
    def ics_url(self) -> str:
        # Points at the real per-jurisdiction feed emitted by the ICS exporter into
        # the site's /downloads/ tree (keyed by the raw slug), so the link resolves.
        return f"/downloads/ics/{self.state}/{self.slug}.ics"

    @property
    def upcoming(self) -> list[ElectionView]:
        return [e for e in self.elections if e.is_upcoming]

    @property
    def next_election(self) -> Optional[ElectionView]:
        up = self.upcoming
        return up[0] if up else None


@dataclass
class StateView:
    code: str
    name: str
    elections: list[ElectionView] = field(default_factory=list)
    jurisdictions: list[JurisdictionView] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"/states/{self.code}/"

    @property
    def election_count(self) -> int:
        return len(self.elections)

    @property
    def jurisdiction_count(self) -> int:
        return len(self.jurisdictions)

    @property
    def upcoming(self) -> list[ElectionView]:
        return [e for e in self.elections if e.is_upcoming]

    @property
    def next_election(self) -> Optional[ElectionView]:
        up = self.upcoming
        return up[0] if up else None


@dataclass
class SiteData:
    version: str
    generated_at: str
    today: datetime.date
    elections: list[ElectionView]
    states: list[StateView]
    jurisdictions: list[JurisdictionView]
    # When True, the build renders a site-wide banner stating the records are
    # illustrative sample data — so a demo build never presents fake elections as real.
    demo: bool = False
    # Open Graph card paths: {"default": "/og/default.png"|None, "elections": {id: path}}.
    og: dict = field(default_factory=dict)

    @property
    def upcoming(self) -> list[ElectionView]:
        return [e for e in self.elections if e.is_upcoming]

    @property
    def total_elections(self) -> int:
        return len(self.elections)

    @property
    def total_states(self) -> int:
        return len(self.states)

    @property
    def total_jurisdictions(self) -> int:
        return len(self.jurisdictions)

    @property
    def type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.elections:
            counts[e.election_type] = counts.get(e.election_type, 0) + 1
        return counts

    @property
    def last_modified(self) -> str:
        """Most recent verified_at across records, for sitemap lastmod. Falls back to
        generated_at."""
        stamps = [e.verified_at for e in self.elections if e.verified_at]
        return max(stamps) if stamps else self.generated_at


def _build_deadlines(rec: dict, today: datetime.date) -> list[Deadline]:
    spec = [
        ("candidate_filing_deadline", "Candidate filing deadline", None),
        ("registration_deadline", "Voter registration deadline", rec.get("registration_deadline_time")),
        ("mail_ballot_request_deadline", "Mail ballot request deadline", None),
        ("early_voting_start", "Early voting begins", None),
        ("early_voting_end", "Early voting ends", None),
    ]
    out: list[Deadline] = []
    for key, label, time in spec:
        d = _parse(rec.get(key))
        if d is not None:
            out.append(Deadline(key=key, label=label, date=d, formatted=fmt_short(d), time=time))
    out.sort(key=lambda x: x.date)
    return out


def _to_view(rec: dict, today: datetime.date) -> ElectionView:
    state = rec["state"]
    etype = rec["election_type"]
    jtype = rec["jurisdiction_type"]
    conf = rec["confidence"]
    return ElectionView(
        id=rec["id"],
        state=state,
        state_name=STATE_NAMES.get(state, state),
        jurisdiction_type=jtype,
        jurisdiction_type_label=JURISDICTION_TYPE_LABELS.get(jtype, jtype),
        jurisdiction_name=rec["jurisdiction_name"],
        jurisdiction_slug=rec["jurisdiction_slug"],
        election_date=datetime.date.fromisoformat(rec["election_date"]),
        election_type=etype,
        election_type_label=ELECTION_TYPE_LABELS.get(etype, etype),
        offices=list(rec.get("offices") or []),
        timezone=rec.get("timezone"),
        status=rec["status"],
        confidence=conf,
        confidence_label=CONFIDENCE_LABELS.get(conf, conf),
        confidence_blurb=CONFIDENCE_BLURB.get(conf, ""),
        source_url=rec["source_url"],
        source_retrieved_at=rec.get("source_retrieved_at"),
        verified_by=rec.get("verified_by"),
        verified_at=rec.get("verified_at"),
        notes=rec.get("notes"),
        deadlines=_build_deadlines(rec, today),
        _today=today,
        url_slug=rec["jurisdiction_slug"],
    )


def load_site_data(
    conn: sqlite3.Connection,
    *,
    version: str,
    generated_at: str,
    today: Optional[datetime.date] = None,
    include_unverified: bool = False,
) -> SiteData:
    """Assemble the full site view model from verified election records."""
    if today is None:
        today = datetime.date.today()

    rows = fetch_elections(conn, include_unverified)
    elections = [_to_view(row_to_record(r), today) for r in rows]
    elections.sort(key=lambda e: (e.election_date, e.state, e.jurisdiction_name))

    # Group into jurisdictions keyed by (state, TYPE, slug) so a county and a city that
    # share a name are never merged into one mislabeled view.
    juris_map: dict[tuple[str, str, str], JurisdictionView] = {}
    for e in elections:
        key = (e.state, e.jurisdiction_type, e.jurisdiction_slug)
        jv = juris_map.get(key)
        if jv is None:
            jv = JurisdictionView(
                state=e.state,
                state_name=e.state_name,
                slug=e.jurisdiction_slug,
                name=e.jurisdiction_name,
                jurisdiction_type=e.jurisdiction_type,
                jurisdiction_type_label=e.jurisdiction_type_label,
            )
            juris_map[key] = jv
        jv.elections.append(e)

    # Disambiguate URL slugs when one state has multiple jurisdiction TYPES sharing a
    # slug, so their hub pages/URLs never collide and overwrite each other.
    per_state_slug: dict[tuple[str, str], list[JurisdictionView]] = {}
    for jv in juris_map.values():
        per_state_slug.setdefault((jv.state, jv.slug), []).append(jv)
    for group in per_state_slug.values():
        if len(group) > 1:
            for jv in group:
                jv.url_slug = f"{jv.slug}-{jv.jurisdiction_type}"
                for e in jv.elections:
                    e.url_slug = jv.url_slug

    state_map: dict[str, StateView] = {}
    for e in elections:
        sv = state_map.get(e.state)
        if sv is None:
            sv = StateView(code=e.state, name=e.state_name)
            state_map[e.state] = sv
        sv.elections.append(e)
    for (st, _jtype, _slug), jv in juris_map.items():
        state_map[st].jurisdictions.append(jv)

    jurisdictions = sorted(juris_map.values(), key=lambda j: (j.state_name, j.name))
    for sv in state_map.values():
        sv.jurisdictions.sort(key=lambda j: j.name)
    states = sorted(state_map.values(), key=lambda s: s.name)

    return SiteData(
        version=version,
        generated_at=generated_at,
        today=today,
        elections=elections,
        states=states,
        jurisdictions=jurisdictions,
    )
