"""Manual YAML intake — Phase 1's primary input path.

Human curation is the moat. An intake file is a YAML list of records. Either every
entry validates and the whole file upserts, or the ENTIRE FILE is rejected with
per-entry, per-field error messages. There is no partial ingestion.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .ids import election_id
from .models import ElectionRecord
from .store import UpsertResult, upsert


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys instead of silently keeping the
    last one (which would let a typo'd second key quietly override the first)."""


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate key {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


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
    try:
        data = yaml.load(raw, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise IntakeError([f"YAML parse error: {exc}"])

    if data is None:
        raise IntakeError(["file is empty; expected a YAML list of records"])
    if not isinstance(data, list):
        raise IntakeError(
            [f"file must contain a YAML list of records, got {type(data).__name__}"]
        )

    records: list[ElectionRecord] = []
    errors: list[str] = []
    seen_ids: dict[str, int] = {}

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(f"[entry {i}] must be a mapping, got {type(entry).__name__}")
            continue
        try:
            record = ElectionRecord(**entry)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(x) for x in err["loc"]) or "<root>"
                errors.append(f"[entry {i}] field '{loc}': {err['msg']}")
            continue
        except TypeError as exc:
            # e.g. a non-string mapping key (YAML `on:` -> bool) reaching **entry.
            errors.append(f"[entry {i}] invalid mapping keys: {exc}")
            continue

        eid = election_id(
            record.state, record.jurisdiction_type, record.jurisdiction_slug,
            record.election_date.isoformat(), record.election_type,
        )
        if eid in seen_ids:
            errors.append(
                f"[entry {i}] duplicate election (same identity as entry "
                f"{seen_ids[eid]}); a file may not contain the same election twice"
            )
            continue
        seen_ids[eid] = i
        records.append(record)

    if errors:
        raise IntakeError(errors)
    return records


def ingest_intake(conn, path: str | Path, actor: str) -> list[UpsertResult]:
    """Validate the whole file, then upsert every record. All-or-nothing: validation
    raises before any write occurs."""
    records = load_intake(path)
    return [upsert(conn, record, actor) for record in records]
