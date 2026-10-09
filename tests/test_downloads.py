"""Open-data downloads and the frontend payload builder."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path

import pytest
from icalendar import Calendar

from civic.downloads import (
    CSV_COLUMNS,
    CSV_NAME,
    ICS_NAME,
    JSON_NAME,
    build_downloads,
    elections_csv,
    elections_ics,
    upcoming,
)
from civic.frontend_data import build_payload, build_records

ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-10-09T05:07:27Z"


def election(**overrides):
    base = {
        "id": "0123456789abcdef", "state": "TX", "state_name": "Texas", "jurisdiction_type": "state",
        "jurisdiction_name": "Texas", "jurisdiction_slug": "texas", "slug": "texas", "election_type": "general",
        "election_date": "2026-11-03", "offices": ["U.S. Senate", "Governor"],
        "registration_deadline": "2026-10-05", "registration_deadline_time": None,
        "early_voting_start": "2026-10-19", "early_voting_end": "2026-10-30",
        "mail_ballot_request_deadline": "2026-10-23", "candidate_filing_deadline": None, "timezone": None,
        "confidence": "official", "source_url": "https://sos.example.gov/tx",
        "source_retrieved_at": "2026-10-09T12:00:00Z", "notes": "Line one, with a comma and \"quotes\".", "verified": True,
    }
    return {**base, **overrides}


def events(ics: bytes):
    return list(Calendar.from_ical(ics).walk("VEVENT"))


def test_csv_round_trips_every_field_and_joins_offices():
    rows = list(csv.DictReader(io.StringIO(elections_csv([election(), election(id="b" * 16, offices=[], early_voting_start=None)]).decode())))
    assert list(rows[0].keys()) == list(CSV_COLUMNS)
    assert rows[0]["offices"] == "U.S. Senate; Governor"
    assert rows[0]["notes"] == 'Line one, with a comma and "quotes".'
    assert rows[1]["offices"] == "" and rows[1]["early_voting_start"] == ""


def test_csv_carries_the_late_registration_classification():
    rows = list(csv.DictReader(io.StringIO(elections_csv([election(late_registration="election_day"), election(id="b" * 16)]).decode())))
    assert rows[0]["late_registration"] == "election_day"
    assert rows[1]["late_registration"] == ""


def test_registration_event_says_what_is_possible_after_the_deadline():
    with_late = {str(e["uid"]): e for e in events(elections_ics([election(late_registration="election_day")], GENERATED_AT))}
    description = str(with_late["0123456789abcdef@midtermwatch.com#registration"]["description"])
    assert "Late registration: Open through Election Day." in description
    without = {str(e["uid"]): e for e in events(elections_ics([election()], GENERATED_AT))}
    assert "Late registration" not in str(without["0123456789abcdef@midtermwatch.com#registration"]["description"])


def test_calendar_has_the_expected_events_and_unique_uids():
    evs = events(elections_ics([election()], GENERATED_AT))
    by_uid = {str(e["uid"]): e for e in evs}
    assert len(by_uid) == len(evs) == 4
    day = by_uid["0123456789abcdef@midtermwatch.com"]
    assert day["dtstart"].dt == dt.date(2026, 11, 3) and day["dtend"].dt == dt.date(2026, 11, 4)
    early = by_uid["0123456789abcdef@midtermwatch.com#early-voting"]
    assert early["dtstart"].dt == dt.date(2026, 10, 19)
    assert early["dtend"].dt == dt.date(2026, 10, 31)  # end date is inclusive, DTEND exclusive
    assert by_uid["0123456789abcdef@midtermwatch.com#registration"]["dtstart"].dt == dt.date(2026, 10, 5)
    assert by_uid["0123456789abcdef@midtermwatch.com#mail-ballot-request"]["dtstart"].dt == dt.date(2026, 10, 23)


def test_calendar_leaves_out_elections_held_before_the_payload_was_generated():
    held = election(id="a" * 16, election_date="2026-09-15", registration_deadline="2026-08-17")
    assert upcoming([held, election()], GENERATED_AT) == [election()]
    assert len(events(elections_ics([held, election()], GENERATED_AT))) == 4


def test_downloads_are_deterministic_and_the_manifest_matches_the_bytes():
    payload = {"edition": "E", "generated_at": GENERATED_AT, "demo": False, "elections": [election()]}
    first, manifest = build_downloads(payload)
    second, again = build_downloads(payload)
    assert first == second and manifest == again
    assert json.loads(first[JSON_NAME]) == payload
    for entry in manifest["files"]:
        data = first[entry["name"]]
        assert entry["bytes"] == len(data) and entry["sha256"] == hashlib.sha256(data).hexdigest()
    assert {entry["name"] for entry in manifest["files"]} == {JSON_NAME, CSV_NAME, ICS_NAME}


def test_unchanged_records_keep_the_previous_payload_and_its_timestamp():
    previous = {"edition": "E", "generated_at": GENERATED_AT, "demo": False, "elections": [election()]}
    payload, changed = build_payload([election()], previous, now=dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc))
    assert payload is previous and changed is False


def test_changed_records_get_a_new_timestamp():
    previous = {"edition": "E", "generated_at": GENERATED_AT, "demo": False, "elections": [election()]}
    payload, changed = build_payload([election(notes="Edited")], previous, now=dt.datetime(2030, 1, 2, 3, 4, 5, 678, tzinfo=dt.timezone.utc))
    assert changed is True and payload["generated_at"] == "2030-01-02T03:04:05Z"


# --- the committed artifacts must be what the generator produces -------------------------


def committed_payload():
    return json.loads((ROOT / "generated" / "elections.json").read_text(encoding="utf-8"))


def test_committed_payload_is_current_with_the_intake_files():
    """A stale generated/elections.json (for example after editing intake/*.yaml by hand
    and forgetting `python scripts/build-frontend-data.py`) must fail here, not on deploy."""
    previous = committed_payload()
    assert build_records(ROOT / "intake", previous) == previous["elections"]


def test_committed_downloads_and_manifest_are_current_with_the_payload():
    payload = committed_payload()
    files, manifest = build_downloads(payload)
    for name, data in files.items():
        assert (ROOT / "public" / "downloads" / name).read_bytes() == data, f"{name} is stale; rerun scripts/build-frontend-data.py"
    committed_manifest = json.loads((ROOT / "generated" / "downloads-manifest.json").read_text(encoding="utf-8"))
    assert committed_manifest == manifest
