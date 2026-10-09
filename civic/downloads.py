"""Open-data downloads for the frontend: JSON, CSV and an ICS reminder calendar.

All three files are derived from the frontend payload (``generated/elections.json``),
so they always describe exactly the records the site shows. Output is deterministic
for a given payload: no wall-clock values are used, ``DTSTAMP`` is the payload's own
``generated_at``.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable

from icalendar import Calendar, Event

from .site.data import ELECTION_TYPE_LABELS

JSON_NAME = "midterm-watch-elections.json"
CSV_NAME = "midterm-watch-elections.csv"
ICS_NAME = "midterm-watch-elections.ics"

CSV_COLUMNS: tuple[str, ...] = (
    "id",
    "state",
    "state_name",
    "jurisdiction_type",
    "jurisdiction_name",
    "election_type",
    "election_date",
    "offices",
    "registration_deadline",
    "registration_deadline_time",
    "early_voting_start",
    "early_voting_end",
    "mail_ballot_request_deadline",
    "candidate_filing_deadline",
    "timezone",
    "confidence",
    "source_url",
    "source_retrieved_at",
    "notes",
)

_DISCLAIMER = "Deadlines can change. Confirm with your state or local election office before you rely on a date."


def upcoming(elections: Iterable[dict[str, Any]], generated_at: str) -> list[dict[str, Any]]:
    """Elections on or after the payload's own generation date.

    Using the payload's timestamp rather than the wall clock keeps the output
    deterministic: the same payload always yields the same calendar.
    """
    as_of = dt.datetime.fromisoformat(generated_at.replace("Z", "+00:00")).date()
    return [rec for rec in elections if dt.date.fromisoformat(rec["election_date"]) >= as_of]


def elections_json(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def elections_csv(elections: Iterable[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for rec in elections:
        row = []
        for col in CSV_COLUMNS:
            value = rec.get(col)
            if col == "offices":
                value = "; ".join(value or [])
            row.append("" if value is None else value)
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _all_day(uid: str, start: dt.date, end: dt.date, summary: str, description: str, stamp: dt.datetime) -> Event:
    ev = Event()
    ev.add("uid", uid)
    ev.add("dtstart", start)
    ev.add("dtend", end + dt.timedelta(days=1))
    ev.add("summary", summary)
    ev.add("description", description)
    ev.add("dtstamp", stamp)
    return ev


def _parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def elections_ics(elections: Iterable[dict[str, Any]], generated_at: str, domain: str = "midtermwatch.com") -> bytes:
    """One calendar of upcoming elections: election day, registration, early voting, mail requests.

    Elections held before the payload was generated are left out; the JSON and CSV keep them.
    """
    stamp = dt.datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    cal = Calendar()
    cal.add("prodid", "-//Midterm Watch//Election dates//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Midterm Watch election dates")
    for rec in upcoming(elections, generated_at):
        name = rec["jurisdiction_name"]
        label = ELECTION_TYPE_LABELS.get(rec["election_type"], rec["election_type"]).lower()
        election_date = _parse_date(rec["election_date"])
        base = f"{rec['id']}@{domain}"
        tail = f"Source: {rec['source_url']}\n{_DISCLAIMER}"
        offices = "; ".join(rec.get("offices") or [])
        lead = f"Offices: {offices}\n" if offices else ""
        cal.add_component(_all_day(
            f"{base}", election_date, election_date, f"{name}: {label} election",
            f"{lead}{tail}", stamp,
        ))
        if rec.get("registration_deadline"):
            when = _parse_date(rec["registration_deadline"])
            at = f" at {rec['registration_deadline_time']}" if rec.get("registration_deadline_time") else ""
            cal.add_component(_all_day(
                f"{base}#registration", when, when, f"{name}: voter registration deadline",
                f"Register by this date{at} to vote in the {rec['election_date']} {label} election. "
                f"Mail, online and in-person deadlines can differ; see the election page.\n{tail}", stamp,
            ))
        if rec.get("early_voting_start"):
            start = _parse_date(rec["early_voting_start"])
            end = _parse_date(rec["early_voting_end"]) if rec.get("early_voting_end") else start
            cal.add_component(_all_day(
                f"{base}#early-voting", start, max(start, end), f"{name}: early voting",
                f"Early voting for the {rec['election_date']} {label} election.\n{tail}", stamp,
            ))
        if rec.get("mail_ballot_request_deadline"):
            when = _parse_date(rec["mail_ballot_request_deadline"])
            cal.add_component(_all_day(
                f"{base}#mail-ballot-request", when, when, f"{name}: mail ballot request deadline",
                f"Last day to request a mail ballot for the {rec['election_date']} {label} election.\n{tail}", stamp,
            ))
    return cal.to_ical()


def _record(name: str, fmt: str, data: bytes, records: int, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "format": fmt,
        "description": description,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "records": records,
    }


def build_downloads(payload: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Return ``({file name: bytes}, manifest)`` for a frontend payload."""
    elections = payload["elections"]
    upcoming_count = len(upcoming(elections, payload["generated_at"]))
    files = {
        JSON_NAME: elections_json(payload),
        CSV_NAME: elections_csv(elections),
        ICS_NAME: elections_ics(elections, payload["generated_at"]),
    }
    manifest = {
        "edition": payload["edition"],
        "generated_at": payload["generated_at"],
        "files": [
            _record(JSON_NAME, "JSON", files[JSON_NAME], len(elections), "Structured records for apps and analysis."),
            _record(CSV_NAME, "CSV", files[CSV_NAME], len(elections), "Flat rows for spreadsheets and reporting."),
            _record(ICS_NAME, "ICS", files[ICS_NAME], upcoming_count, "Upcoming elections and deadlines for your calendar."),
        ],
    }
    return files, manifest


def write_downloads(payload: dict[str, Any], out_dir: Path, manifest_path: Path) -> dict[str, Any]:
    """Write the download files and their manifest; return the manifest."""
    files, manifest = build_downloads(payload)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out_dir / name).write_bytes(data)
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
