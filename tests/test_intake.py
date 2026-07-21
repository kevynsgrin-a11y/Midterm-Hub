"""Intake: whole-file all-or-nothing validation with indexed errors."""
from __future__ import annotations

from pathlib import Path

import pytest

from civic.intake import IntakeError, ingest_intake, load_intake

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
