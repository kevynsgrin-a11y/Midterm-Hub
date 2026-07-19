"""ICS export — the consumer differentiator ("add your town's election calendar").

One ``.ics`` file per jurisdiction. Each election becomes an all-day VEVENT; when a
registration deadline is present, a second all-day VEVENT is emitted for it. Files
must round-trip through the ``icalendar`` parser.
"""
from __future__ import annotations

import datetime
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from icalendar import Calendar, Event

from . import fetch_elections, record_export_run, row_to_record, sha256_file


def _all_day_event(
    uid: str, start: datetime.date, summary: str, description: str, dtstamp: datetime.datetime
) -> Event:
    ev = Event()
    ev.add("uid", uid)
    # A `date` (not datetime) value makes this an all-day event.
    ev.add("dtstart", start)
    ev.add("dtend", start + datetime.timedelta(days=1))
    ev.add("summary", summary)
    ev.add("description", description)
    ev.add("dtstamp", dtstamp)
    return ev


def export_ics(
    conn: sqlite3.Connection,
    out_dir: str | Path,
    version: str,
    generated_at: str,
    generated_at_dt: datetime.datetime,
    ics_domain: str,
    include_unverified: bool = False,
) -> list[dict[str, str]]:
    """Emit one calendar per jurisdiction; record the export run."""
    rows = fetch_elections(conn, include_unverified)
    by_juris: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rec = row_to_record(row)
        by_juris[(rec["state"], rec["jurisdiction_slug"])].append(rec)

    base = Path(out_dir) / "ics"
    manifest: list[dict[str, str]] = []

    for (state, slug), records in sorted(by_juris.items()):
        cal = Calendar()
        cal.add("prodid", "-//civic-calendar-engine//off-cycle elections//EN")
        cal.add("version", "2.0")

        for rec in sorted(records, key=lambda r: r["election_date"]):
            election_date = datetime.date.fromisoformat(rec["election_date"])
            reg = rec.get("registration_deadline")
            desc_parts = []
            if reg:
                desc_parts.append(f"Registration deadline: {reg}")
            desc_parts.append(f"Source: {rec['source_url']}")
            description = "\n".join(desc_parts)

            cal.add_component(
                _all_day_event(
                    uid=f"{rec['id']}@{ics_domain}",
                    start=election_date,
                    summary=f"{rec['jurisdiction_name']} — {rec['election_type']} election",
                    description=description,
                    dtstamp=generated_at_dt,
                )
            )

            if reg:
                reg_date = datetime.date.fromisoformat(reg)
                cal.add_component(
                    _all_day_event(
                        uid=f"{rec['id']}-reg@{ics_domain}",
                        start=reg_date,
                        summary=(
                            f"{rec['jurisdiction_name']} — voter registration deadline"
                        ),
                        description=(
                            f"Registration deadline for the "
                            f"{rec['election_date']} {rec['election_type']} election.\n"
                            f"Source: {rec['source_url']}"
                        ),
                        dtstamp=generated_at_dt,
                    )
                )

        ics_path = base / state / f"{slug}.ics"
        ics_path.parent.mkdir(parents=True, exist_ok=True)
        ics_path.write_bytes(cal.to_ical())
        manifest.append({"path": str(ics_path), "sha256": sha256_file(ics_path)})

    record_export_run(conn, version, "ics", len(rows), manifest, generated_at)
    return manifest
