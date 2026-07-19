"""Pydantic v2 models and validators for election records.

``ElectionRecord`` mirrors the ``elections`` table minus DB bookkeeping fields
(id, content_hash, created_at, updated_at) and workflow-managed fields (status,
verified_by, verified_at, which are set exclusively through the store's audited
transitions). Ordering anomalies are surfaced as non-fatal ``warnings`` because
state law has legitimately odd cases; only genuinely disqualifying conditions
raise hard validation errors.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .ids import slugify

# Canonical set of postal codes: 50 states + DC.
STATES: frozenset[str] = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    }
)

JurisdictionType = Literal[
    "state", "county", "municipality", "school_district", "special_district"
]
ElectionType = Literal[
    "primary", "general", "runoff", "special", "municipal", "school_board", "ballot_measure"
]
Confidence = Literal["official", "secondary", "inferred"]

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")

# Fields that must parse strictly as civil ISO dates (never datetimes).
_DATE_FIELDS = (
    "election_date",
    "registration_deadline",
    "early_voting_start",
    "early_voting_end",
    "mail_ballot_request_deadline",
    "candidate_filing_deadline",
)


def _parse_iso_date(value: Any) -> Optional[datetime.date]:
    """Strictly parse an ISO 8601 civil date. Rejects datetimes and non-ISO input."""
    if value is None:
        return None
    # datetime is a subclass of date, so check it first and reject it.
    if isinstance(value, datetime.datetime):
        raise ValueError("must be a civil date (YYYY-MM-DD), not a datetime")
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid ISO 8601 date: {value!r}") from exc
    raise ValueError(f"invalid date value: {value!r}")


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class ElectionRecord(BaseModel):
    """A validated, hashable election record."""

    model_config = ConfigDict(extra="forbid")

    state: str
    jurisdiction_type: JurisdictionType
    jurisdiction_name: str
    jurisdiction_slug: str = ""
    election_date: datetime.date
    election_type: ElectionType
    offices: list[str] = Field(default_factory=list)
    registration_deadline: Optional[datetime.date] = None
    registration_deadline_time: Optional[str] = None
    early_voting_start: Optional[datetime.date] = None
    early_voting_end: Optional[datetime.date] = None
    mail_ballot_request_deadline: Optional[datetime.date] = None
    candidate_filing_deadline: Optional[datetime.date] = None
    timezone: Optional[str] = None
    confidence: Confidence = "secondary"
    source_url: str
    source_retrieved_at: datetime.datetime = Field(default_factory=_utcnow)
    notes: Optional[str] = None

    # Non-fatal ordering anomalies, excluded from serialization and hashing.
    warnings: list[str] = Field(default_factory=list, exclude=True)

    # --- field-level validators -------------------------------------------------

    @field_validator("state", mode="before")
    @classmethod
    def _check_state(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("state must be a 2-letter postal code string")
        code = v.strip().upper()
        if code not in STATES:
            raise ValueError(f"unknown state postal code: {v!r}")
        return code

    @field_validator(*_DATE_FIELDS, mode="before")
    @classmethod
    def _strict_dates(cls, v: Any) -> Optional[datetime.date]:
        return _parse_iso_date(v)

    @field_validator("registration_deadline_time")
    @classmethod
    def _check_time(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("registration_deadline_time must match HH:MM")
        return v

    @field_validator("offices")
    @classmethod
    def _check_offices(cls, v: list[str]) -> list[str]:
        for office in v:
            if not isinstance(office, str) or not office.strip():
                raise ValueError("offices must be a list of non-empty strings")
        return v

    @field_validator("source_retrieved_at", mode="before")
    @classmethod
    def _parse_retrieved(cls, v: Any) -> datetime.datetime:
        if isinstance(v, datetime.datetime):
            return v
        if isinstance(v, datetime.date):
            return datetime.datetime(v.year, v.month, v.day, tzinfo=datetime.timezone.utc)
        if isinstance(v, str):
            return datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        raise ValueError("source_retrieved_at must be a datetime or ISO string")

    # --- whole-model validators -------------------------------------------------

    @model_validator(mode="before")
    @classmethod
    def _derive_slug(cls, data: Any) -> Any:
        if isinstance(data, dict):
            slug = data.get("jurisdiction_slug")
            name = data.get("jurisdiction_name")
            if not slug and isinstance(name, str) and name.strip():
                data = {**data, "jurisdiction_slug": slugify(name)}
        return data

    @model_validator(mode="after")
    def _ordering_and_recency(self) -> "ElectionRecord":
        warnings: list[str] = []
        ed = self.election_date

        if self.registration_deadline and self.registration_deadline > ed:
            warnings.append(
                f"registration_deadline ({self.registration_deadline}) is after "
                f"election_date ({ed})"
            )
        if self.candidate_filing_deadline and self.candidate_filing_deadline >= ed:
            warnings.append(
                f"candidate_filing_deadline ({self.candidate_filing_deadline}) is not "
                f"before election_date ({ed})"
            )
        evs, eve = self.early_voting_start, self.early_voting_end
        if evs and eve and evs > eve:
            warnings.append(
                f"early_voting_start ({evs}) is after early_voting_end ({eve})"
            )
        if eve and eve > ed:
            warnings.append(
                f"early_voting_end ({eve}) is after election_date ({ed})"
            )
        if evs and not eve and evs > ed:
            warnings.append(
                f"early_voting_start ({evs}) is after election_date ({ed})"
            )
        # Assign without re-triggering validation.
        object.__setattr__(self, "warnings", warnings)

        # Hard failure: stale record without an explicit historical-backfill marker.
        age_days = (datetime.date.today() - ed).days
        if age_days > 30 and "historical" not in (self.notes or "").lower():
            raise ValueError(
                f"election_date {ed} is more than 30 days in the past; add "
                f"'historical' to notes to intentionally backfill"
            )
        return self

    # --- helpers ----------------------------------------------------------------

    def slug(self) -> str:
        return self.jurisdiction_slug
