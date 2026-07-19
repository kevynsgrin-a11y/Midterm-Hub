"""JSON export for the Utility Engine static build.

Writes ``{out}/json/{state}/index.json`` (all exported elections for the state) and
``{out}/json/{state}/{jurisdiction_slug}.json`` (per-jurisdiction), each with a fixed
top-level shape.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import fetch_elections, record_export_run, row_to_record, sha256_file


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def export_json(
    conn: sqlite3.Connection,
    out_dir: str | Path,
    version: str,
    generated_at: str,
    include_unverified: bool = False,
) -> list[dict[str, str]]:
    """Emit per-state and per-jurisdiction JSON files; record the export run."""
    rows = fetch_elections(conn, include_unverified)
    by_state: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_state[row["state"]].append(row_to_record(row))

    base = Path(out_dir) / "json"
    manifest: list[dict[str, str]] = []

    def envelope(state: str, elections: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "generated_at": generated_at,
            "version": version,
            "state": state,
            "includes_unverified": include_unverified,
            "elections": elections,
        }

    for state, records in sorted(by_state.items()):
        records_sorted = sorted(records, key=lambda r: (r["election_date"], r["jurisdiction_slug"]))

        index_path = base / state / "index.json"
        _write_json(index_path, envelope(state, records_sorted))
        manifest.append({"path": str(index_path), "sha256": sha256_file(index_path)})

        by_slug: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rec in records_sorted:
            by_slug[rec["jurisdiction_slug"]].append(rec)
        for slug, slug_records in sorted(by_slug.items()):
            slug_path = base / state / f"{slug}.json"
            _write_json(slug_path, envelope(state, slug_records))
            manifest.append({"path": str(slug_path), "sha256": sha256_file(slug_path)})

    record_export_run(conn, version, "json", len(rows), manifest, generated_at)
    return manifest
