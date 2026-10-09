"""Build the frontend election payload from curated intake files.

The intake files remain the source of truth. Every record is validated by the same
Pydantic model as the audited pipeline before it is serialized. An unchanged,
previously published archive record keeps validating after its election ages out
(see ``civic.intake.published_index``).
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Any, Optional

import yaml

from .intake import published_index, published_key
from .models import ElectionRecord
from .site.data import STATE_NAMES

EDITION = "2026 Midterm Cycle"


def slug(value: str) -> str:
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in value).split())


def build_records(intake_dir: Path, previous: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate every intake record and return the serialized, sorted election rows."""
    published = published_index(previous)
    records: list[dict[str, Any]] = []
    for path in sorted(Path(intake_dir).glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            record = ElectionRecord.model_validate(
                raw, context={"previously_published": published.get(published_key(raw))}
            )
            data = record.model_dump(mode="json")
            identity = f"{record.state}|{record.jurisdiction_name}|{record.election_type}|{record.election_date}"
            data["id"] = hashlib.sha256(identity.encode()).hexdigest()[:16]
            data["state_name"] = STATE_NAMES.get(record.state, record.state)
            data["slug"] = slug(record.jurisdiction_name)
            data["verified"] = True
            records.append(data)
    records.sort(key=lambda x: (x["election_date"], x["state"], x["jurisdiction_name"]))
    return records


def build_payload(
    records: list[dict[str, Any]],
    previous: dict[str, Any],
    now: Optional[dt.datetime] = None,
) -> tuple[dict[str, Any], bool]:
    """Return ``(payload, changed)``.

    Rebuilding the same data does not mean its sources were reviewed today, so an
    unchanged record set keeps the previous payload and its ``generated_at``.
    """
    if records == previous.get("elections"):
        return previous, False
    stamp = (now or dt.datetime.now(dt.timezone.utc)).replace(microsecond=0)
    payload = {
        "edition": EDITION,
        "generated_at": stamp.isoformat().replace("+00:00", "Z"),
        "demo": False,
        "elections": records,
    }
    return payload, True
