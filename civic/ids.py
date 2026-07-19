"""Deterministic identity, content hashing, and slugify.

Determinism is the backbone of idempotent ingestion: the same real-world election
always maps to the same row id, and a record's substantive content always hashes to
the same value regardless of bookkeeping fields or key ordering.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping

# The exact, ordered list of fields that define a record's substance. Anything not
# in this list (status, source_url, retrieval/verification metadata, notes,
# timestamps) is intentionally excluded from the content hash so that re-fetching or
# re-annotating a record does not spuriously register as a data change.
SUBSTANTIVE_FIELDS: tuple[str, ...] = (
    "state",
    "jurisdiction_type",
    "jurisdiction_name",
    "jurisdiction_slug",
    "election_date",
    "election_type",
    "offices",
    "registration_deadline",
    "registration_deadline_time",
    "early_voting_start",
    "early_voting_end",
    "mail_ballot_request_deadline",
    "candidate_filing_deadline",
    "timezone",
    "confidence",
)

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Lowercase, NFKD-normalize and strip non-ASCII, collapse non-[a-z0-9] runs into
    single hyphens, and strip leading/trailing hyphens."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _NON_SLUG.sub("-", ascii_only.lower())
    return slug.strip("-")


def election_id(
    state: str, jurisdiction_slug: str, election_date: str, election_type: str
) -> str:
    """First 16 hex chars of sha256 over the identity tuple, with state uppercased.

    ``election_date`` must already be an ISO date string (YYYY-MM-DD).
    """
    key = f"{state.upper()}|{jurisdiction_slug}|{election_date}|{election_type}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _coerce(value: Any) -> Any:
    """Render date/datetime values as ISO strings for stable canonical JSON."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def _substantive_view(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        data = {k: record.get(k) for k in SUBSTANTIVE_FIELDS}
    else:
        data = {k: getattr(record, k) for k in SUBSTANTIVE_FIELDS}
    return {k: _coerce(v) for k, v in data.items()}


def content_hash(record: Any) -> str:
    """sha256 of canonical JSON (sorted keys, no whitespace) over the substantive
    fields only.

    Accepts a mapping or any object exposing the substantive fields as attributes.
    ``offices`` is expected as a list; dates may be ``date`` objects or ISO strings.
    """
    view = _substantive_view(record)
    canonical = json.dumps(
        view, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
