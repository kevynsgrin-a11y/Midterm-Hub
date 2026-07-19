"""Export helpers shared by the JSON, CSV, and ICS exporters.

Exporters read only ``status='verified'`` records by default. ``include_unverified``
widens the selection to staging statuses (unverified/needs_review) and, in JSON,
stamps ``includes_unverified: true``. Superseded and cancelled records are never
exported. Every export run records a sha256 file manifest in ``export_runs``.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

# Data fields carried into exports, in a stable order. Excludes DB bookkeeping
# (content_hash, created_at, updated_at) but keeps the deterministic id and the
# provenance/verification metadata consumers rely on.
EXPORT_FIELDS: tuple[str, ...] = (
    "id",
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
    "status",
    "confidence",
    "source_url",
    "source_retrieved_at",
    "verified_by",
    "verified_at",
    "notes",
)


def fetch_elections(
    conn: sqlite3.Connection, include_unverified: bool = False
) -> list[sqlite3.Row]:
    """Return exportable election rows sorted by (state, election_date)."""
    if include_unverified:
        statuses = ("verified", "unverified", "needs_review")
    else:
        statuses = ("verified",)
    placeholders = ",".join("?" for _ in statuses)
    return conn.execute(
        f"SELECT * FROM elections WHERE status IN ({placeholders}) "
        f"ORDER BY state, election_date, jurisdiction_slug",
        statuses,
    ).fetchall()


def row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    """Project a DB row to an export record dict (offices decoded to a list)."""
    record: dict[str, Any] = {}
    for field in EXPORT_FIELDS:
        record[field] = row[field]
    record["offices"] = json.loads(row["offices"]) if row["offices"] else []
    return record


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def record_export_run(
    conn: sqlite3.Connection,
    version: str,
    kind: str,
    record_count: int,
    manifest: list[dict[str, str]],
    created_at: str,
) -> None:
    conn.execute(
        "INSERT INTO export_runs (version, kind, record_count, file_manifest, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (version, kind, record_count, json.dumps(manifest), created_at),
    )
