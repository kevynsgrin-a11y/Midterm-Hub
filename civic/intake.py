"""Manual YAML intake — Phase 1's primary input path.

Human curation is the moat. An intake file is a YAML list of records. Either every
entry validates and the whole file upserts, or the ENTIRE FILE is rejected with
per-entry, per-field error messages. There is no partial ingestion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml
from pydantic import ValidationError

from .ids import election_id
from .models import ElectionRecord
from .store import UpsertResult, upsert

PublishedIndex = Mapping[tuple[str, str, str, str], dict[str, Any]]


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


def published_key(entry: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Identity under which an intake entry is matched to a published record."""
    return (
        str(entry.get("state", "")).strip().upper(),
        str(entry.get("jurisdiction_name")),
        str(entry.get("election_type")),
        str(entry.get("election_date")),
    )


def published_index(payload: Mapping[str, Any]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """Index the verified records of a frontend payload (generated/elections.json) by
    ``published_key``, keeping only the fields ``ElectionRecord`` itself serializes."""
    return {
        published_key(item): {
            key: value
            for key, value in item.items()
            if key in ElectionRecord.model_fields and key != "warnings"
        }
        for item in payload.get("elections", [])
        if item.get("verified") is True
    }


def load_published(path: str | Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """Read a frontend payload file into a ``published_index``. Raises IntakeError if
    the file is unreadable, so a bad path can never silently disable the archive."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IntakeError([f"cannot read published payload {path}: {exc}"])
    if not isinstance(payload, dict):
        raise IntakeError(
            [f"published payload {path} must be a JSON object, got {type(payload).__name__}"]
        )
    return published_index(payload)


def load_intake(
    path: str | Path, published: Optional[PublishedIndex] = None
) -> list[ElectionRecord]:
    """Parse and validate an intake file into records. Raises IntakeError on any
    problem, having first collected errors across all entries.

    ``published`` (see ``load_published``) lets an entry that is byte-for-byte the
    record already published stay in the archive past the 30-day recency window.
    Without it, or for any new or edited entry, the recency gate applies in full."""
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
            record = ElectionRecord.model_validate(
                entry,
                context={"previously_published": (published or {}).get(published_key(entry))},
            )
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


def ingest_intake(
    conn, path: str | Path, actor: str, published: Optional[PublishedIndex] = None
) -> list[UpsertResult]:
    """Validate the whole file, then upsert every record. All-or-nothing: validation
    raises before any write occurs."""
    records = load_intake(path, published)
    return [upsert(conn, record, actor) for record in records]
