"""Manual YAML intake — Phase 1's primary input path.

Human curation is the moat. An intake file is a YAML list of records. Either every
entry validates and the whole file upserts, or the ENTIRE FILE is rejected with
per-entry, per-field error messages. There is no partial ingestion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import ElectionRecord
from .store import UpsertResult, upsert


class IntakeError(Exception):
    """Raised when an intake file fails validation. Carries a list of human-readable,
    indexed error strings covering every offending entry/field."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(
            f"intake validation failed with {len(errors)} error(s):\n"
            + "\n".join(errors)
        )


def load_intake(path: str | Path) -> list[ElectionRecord]:
    """Parse and validate an intake file into records. Raises IntakeError on any
    problem, having first collected errors across all entries."""
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    if data is None:
        raise IntakeError(["file is empty; expected a YAML list of records"])
    if not isinstance(data, list):
        raise IntakeError(
            [f"file must contain a YAML list of records, got {type(data).__name__}"]
        )

    records: list[ElectionRecord] = []
    errors: list[str] = []

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(f"[entry {i}] must be a mapping, got {type(entry).__name__}")
            continue
        try:
            records.append(ElectionRecord(**entry))
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(x) for x in err["loc"]) or "<root>"
                errors.append(f"[entry {i}] field '{loc}': {err['msg']}")

    if errors:
        raise IntakeError(errors)
    return records


def ingest_intake(conn, path: str | Path, actor: str) -> list[UpsertResult]:
    """Validate the whole file, then upsert every record. All-or-nothing: validation
    raises before any write occurs."""
    records = load_intake(path)
    return [upsert(conn, record, actor) for record in records]
