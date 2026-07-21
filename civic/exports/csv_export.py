"""CSV export — the B2B product — plus a generated CHANGELOG.

The header row is golden-tested and must match the spec byte-for-byte. ``offices`` is
serialized as a semicolon-joined string. Alongside the CSV, a ``CHANGELOG.md`` is
generated from ``diff_since`` (default: since the previous csv export run).
"""
from __future__ import annotations

import csv
import io
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from ..store import diff_since
from . import fetch_elections, record_export_run, row_to_record, sha256_file

# EXACT header row, golden-tested. Do not reorder or rename.
CSV_HEADER: tuple[str, ...] = (
    "id",
    "state",
    "jurisdiction_type",
    "jurisdiction_name",
    "election_date",
    "election_type",
    "offices",
    "registration_deadline",
    "early_voting_start",
    "early_voting_end",
    "mail_ballot_request_deadline",
    "candidate_filing_deadline",
    "confidence",
    "source_url",
    "verified_at",
)


def _row_values(rec: dict[str, Any]) -> list[str]:
    def s(v: Any) -> str:
        return "" if v is None else str(v)

    return [
        s(rec["id"]),
        s(rec["state"]),
        s(rec["jurisdiction_type"]),
        s(rec["jurisdiction_name"]),
        s(rec["election_date"]),
        s(rec["election_type"]),
        ";".join(rec["offices"]),
        s(rec["registration_deadline"]),
        s(rec["early_voting_start"]),
        s(rec["early_voting_end"]),
        s(rec["mail_ballot_request_deadline"]),
        s(rec["candidate_filing_deadline"]),
        s(rec["confidence"]),
        s(rec["source_url"]),
        s(rec["verified_at"]),
    ]


def _previous_csv_since(conn: sqlite3.Connection) -> str:
    """Date floor for the changelog: the previous csv export's date, else epoch."""
    row = conn.execute(
        "SELECT created_at FROM export_runs WHERE kind = 'csv' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row and row["created_at"]:
        # Full timestamp (not just the date) so a second export the same day doesn't
        # re-list records already reported by the earlier one.
        return row["created_at"]
    return "1970-01-01"


def _render_changelog(
    conn: sqlite3.Connection, since: str, version: str, generated_at: str,
    include_unverified: bool = False,
) -> str:
    # The changelog ships alongside the verified-only CSV, so it must apply the SAME
    # status filter — otherwise unverified records leak into a verified export artifact.
    allowed = (
        {"verified", "unverified", "needs_review"} if include_unverified else {"verified"}
    )
    groups = [g for g in diff_since(conn, since) if g["election"]["status"] in allowed]
    by_state: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for g in groups:
        by_state[g["election"]["state"]].append(g)

    lines: list[str] = [
        f"# Changelog — {version}",
        "",
        f"Generated at {generated_at}. Changes since {since}.",
        "",
    ]
    if not groups:
        lines.append("_No new records or applied changes in this window._")
        lines.append("")
        return "\n".join(lines)

    for state in sorted(by_state):
        lines.append(f"## {state}")
        lines.append("")
        for g in by_state[state]:
            e = g["election"]
            label = f"{e['jurisdiction_name']} — {e['election_type']} ({e['election_date']})"
            if g["is_new"]:
                lines.append(f"- **New record**: {label} `[{e['id']}]`")
            else:
                lines.append(f"- **Updated**: {label} `[{e['id']}]`")
            for c in g["changes"]:
                old = c["old_value"] if c["old_value"] is not None else "∅"
                new = c["new_value"] if c["new_value"] is not None else "∅"
                lines.append(f"  - `{c['field']}`: {old} → {new}")
        lines.append("")
    return "\n".join(lines)


def export_csv(
    conn: sqlite3.Connection,
    out_dir: str | Path,
    version: str,
    generated_at: str,
    include_unverified: bool = False,
    since: Optional[str] = None,
) -> list[dict[str, str]]:
    """Write the versioned CSV and CHANGELOG.md; record the export run."""
    rows = fetch_elections(conn, include_unverified)

    # Resolve the changelog window BEFORE inserting this run's export_runs row.
    if since is None:
        since = _previous_csv_since(conn)

    target = Path(out_dir) / "csv" / version
    target.mkdir(parents=True, exist_ok=True)
    csv_path = target / f"off_cycle_elections_{version}.csv"

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for row in rows:
        writer.writerow(_row_values(row_to_record(row)))
    csv_path.write_text(buf.getvalue(), encoding="utf-8")

    changelog_path = target / "CHANGELOG.md"
    changelog_path.write_text(
        _render_changelog(conn, since, version, generated_at, include_unverified),
        encoding="utf-8",
    )

    manifest = [
        {"path": str(csv_path), "sha256": sha256_file(csv_path)},
        {"path": str(changelog_path), "sha256": sha256_file(changelog_path)},
    ]
    record_export_run(conn, version, "csv", len(rows), manifest, generated_at)
    return manifest
