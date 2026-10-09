"""Intake: whole-file all-or-nothing validation with indexed errors."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from civic.intake import (
    IntakeError,
    ingest_intake,
    load_intake,
    load_published,
    published_index,
)
from civic.models import ElectionRecord

FIXTURES = Path(__file__).parent / "fixtures"


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "intake.yaml"
    p.write_text(text, encoding="utf-8")
    return p


GOOD = """
- state: VA
  jurisdiction_type: municipality
  jurisdiction_name: "Town of Alpha"
  election_type: municipal
  election_date: "2027-05-04"
  offices: ["Mayor"]
  source_url: "https://elections.example.gov/alpha"
- state: NJ
  jurisdiction_type: municipality
  jurisdiction_name: "Borough of Beta"
  election_type: general
  election_date: "2027-11-02"
  source_url: "https://elections.example.gov/beta"
"""


def test_good_file_loads_all(tmp_path):
    records = load_intake(_write(tmp_path, GOOD))
    assert len(records) == 2
    assert records[0].jurisdiction_slug == "town-of-alpha"


def test_good_file_upserts_all(conn, tmp_path):
    results = ingest_intake(conn, _write(tmp_path, GOOD), actor="curator")
    assert len(results) == 2
    assert all(r.action == "inserted" for r in results)
    assert conn.execute("SELECT COUNT(*) FROM elections").fetchone()[0] == 2


def test_bad_entry_rejects_entire_file(conn, tmp_path):
    bad = """
- state: VA
  jurisdiction_type: municipality
  jurisdiction_name: "Town of Alpha"
  election_type: municipal
  election_date: "2027-05-04"
  source_url: "https://elections.example.gov/alpha"
- state: ZZ
  jurisdiction_type: municipality
  jurisdiction_name: "Bad State Town"
  election_type: municipal
  election_date: "2027-05-04"
  source_url: "https://elections.example.gov/bad"
"""
    path = _write(tmp_path, bad)
    with pytest.raises(IntakeError) as exc:
        ingest_intake(conn, path, actor="curator")
    # Errors are indexed by entry and name the offending field.
    errors = exc.value.errors
    assert any("[entry 1]" in e and "state" in e for e in errors)
    # NOTHING was written — the whole file was rejected.
    assert conn.execute("SELECT COUNT(*) FROM elections").fetchone()[0] == 0


def test_multiple_errors_all_reported(tmp_path):
    bad = """
- state: ZZ
  jurisdiction_type: municipality
  jurisdiction_name: "X"
  election_type: municipal
  election_date: "not-a-date"
  source_url: "https://x"
"""
    with pytest.raises(IntakeError) as exc:
        load_intake(_write(tmp_path, bad))
    errors = exc.value.errors
    assert any("state" in e for e in errors)
    assert any("election_date" in e for e in errors)


def test_non_list_file_rejected(tmp_path):
    with pytest.raises(IntakeError):
        load_intake(_write(tmp_path, "state: VA\n"))


def test_duplicate_election_in_file_rejects(conn, tmp_path):
    dup = """
- state: VA
  jurisdiction_type: municipality
  jurisdiction_name: "Town of Alpha"
  election_type: municipal
  election_date: "2027-05-04"
  source_url: "https://x/1"
- state: VA
  jurisdiction_type: municipality
  jurisdiction_name: "Town of Alpha"
  election_type: municipal
  election_date: "2027-05-04"
  source_url: "https://x/2"
"""
    with pytest.raises(IntakeError) as exc:
        ingest_intake(conn, _write(tmp_path, dup), actor="c")
    assert any("duplicate election" in e for e in exc.value.errors)
    assert conn.execute("SELECT COUNT(*) FROM elections").fetchone()[0] == 0


def test_non_string_key_rejected_cleanly(conn, tmp_path):
    # PyYAML coerces `on:` to boolean True — must surface as an IntakeError, not a crash.
    bad = """
- state: VA
  jurisdiction_type: municipality
  jurisdiction_name: "Town of Alpha"
  election_type: municipal
  election_date: "2027-05-04"
  source_url: "https://x/1"
  on: something
"""
    with pytest.raises(IntakeError):
        ingest_intake(conn, _write(tmp_path, bad), actor="c")
    assert conn.execute("SELECT COUNT(*) FROM elections").fetchone()[0] == 0


def test_duplicate_yaml_key_rejected(tmp_path):
    dup_key = """
- state: VA
  state: NJ
  jurisdiction_type: municipality
  jurisdiction_name: "Town of Alpha"
  election_type: municipal
  election_date: "2027-05-04"
  source_url: "https://x/1"
"""
    with pytest.raises(IntakeError):
        load_intake(_write(tmp_path, dup_key))


def test_sample_fixture_is_valid(conn):
    """The shipped sample_intake.yaml must load and upsert cleanly."""
    results = ingest_intake(conn, FIXTURES / "sample_intake.yaml", actor="curator")
    assert len(results) == 4
    assert conn.execute("SELECT COUNT(*) FROM elections").fetchone()[0] == 4


# --- archive window: an unchanged published record outlives the 30-day gate ---------

_STALE_DATE = (dt.date.today() - dt.timedelta(days=60)).isoformat()
_STALE = f"""
- state: CA
  jurisdiction_type: state
  jurisdiction_name: "California"
  election_type: general
  election_date: "{_STALE_DATE}"
  offices: ["State assembly"]
  confidence: official
  source_url: "https://example.gov/elections"
  source_retrieved_at: "2026-01-01T00:00:00Z"
  notes: "Published election record"
"""


def _payload(tmp_path: Path, verified: bool = True, **changes) -> Path:
    """A generated/elections.json holding the stale record above. A stale record can
    only be built with the 'historical' marker, so age a fresh-dated twin instead."""
    twin = ElectionRecord(
        state="CA", jurisdiction_type="state", jurisdiction_name="California",
        election_type="general", election_date=dt.date.today().isoformat(),
        offices=["State assembly"], confidence="official",
        source_url="https://example.gov/elections",
        source_retrieved_at="2026-01-01T00:00:00Z", notes="Published election record",
    ).model_dump(mode="json")
    item = {
        **twin, "election_date": _STALE_DATE, **changes,
        "id": "0123456789abcdef", "state_name": "California", "slug": "california",
        "verified": verified,
    }
    path = tmp_path / "elections.json"
    path.write_text(json.dumps({"elections": [item]}), encoding="utf-8")
    return path


def test_stale_entry_rejected_without_published_payload(tmp_path):
    with pytest.raises(IntakeError, match="more than 30 days"):
        load_intake(_write(tmp_path, _STALE))


def test_unchanged_published_stale_entry_is_accepted(tmp_path):
    published = load_published(_payload(tmp_path))
    (record,) = load_intake(_write(tmp_path, _STALE), published)
    assert record.election_date.isoformat() == _STALE_DATE


@pytest.mark.parametrize("changes", [
    {"source_url": "https://example.gov/older"},
    {"offices": ["Governor"]},
    {"notes": "Edited since publication"},
    {"source_retrieved_at": "2026-02-01T00:00:00Z"},
])
def test_edited_stale_entry_still_needs_historical_marker(tmp_path, changes):
    published = load_published(_payload(tmp_path, **changes))
    with pytest.raises(IntakeError, match="more than 30 days"):
        load_intake(_write(tmp_path, _STALE), published)


def test_unverified_published_copy_does_not_unlock_archive(tmp_path):
    published = load_published(_payload(tmp_path, verified=False))
    assert published == {}
    with pytest.raises(IntakeError, match="more than 30 days"):
        load_intake(_write(tmp_path, _STALE), published)


def test_published_copy_of_a_different_election_does_not_unlock_archive(tmp_path):
    published = load_published(_payload(tmp_path, election_type="primary"))
    with pytest.raises(IntakeError, match="more than 30 days"):
        load_intake(_write(tmp_path, _STALE), published)


def test_published_context_does_not_bypass_structural_validation(tmp_path):
    published = load_published(_payload(tmp_path))
    with pytest.raises(IntakeError) as exc:
        load_intake(_write(tmp_path, _STALE.replace("state: CA", "state: ZZ")), published)
    assert any("[entry 0]" in e and "state" in e for e in exc.value.errors)


def test_published_index_keeps_only_record_fields(tmp_path):
    index = published_index(json.loads(_payload(tmp_path).read_text(encoding="utf-8")))
    (record,) = index.values()
    assert set(record) == set(ElectionRecord.model_fields) - {"warnings"}
    assert record["election_date"] == _STALE_DATE


@pytest.mark.parametrize("content", ["not json", "[]", ""])
def test_unreadable_published_payload_is_an_error(tmp_path, content):
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    with pytest.raises(IntakeError, match="published payload"):
        load_published(bad)


def test_missing_published_payload_is_an_error(tmp_path):
    with pytest.raises(IntakeError, match="cannot read published payload"):
        load_published(tmp_path / "absent.json")


def test_cli_published_flag_ingests_unchanged_archive(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from civic.cli import app

    monkeypatch.setenv("CIVIC_DB_PATH", str(tmp_path / "cli.db"))
    intake_file, payload = _write(tmp_path, _STALE), _payload(tmp_path)
    runner = CliRunner()

    rejected = runner.invoke(app, ["intake", str(intake_file), "--by", "t"])
    assert rejected.exit_code == 1
    assert "more than 30 days" in rejected.output

    accepted = runner.invoke(app, ["intake", str(intake_file), "--by", "t", "--published", str(payload)])
    assert accepted.exit_code == 0, accepted.output
    assert "Ingested 1 record(s)" in accepted.output
