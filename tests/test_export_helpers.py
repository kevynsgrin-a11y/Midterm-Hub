"""Shared export helpers in civic.exports.

These are the functions every exporter (json/csv/ics) depends on, so a bug here
corrupts all three artifacts at once. The invariants under test: a stable field
order, no DB bookkeeping leaking to consumers, offices round-tripped from JSON
back to a real list, status filtering that never emits superseded/cancelled
records, and a sha256 that matches the bytes actually written.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from civic.exports import (
    EXPORT_FIELDS,
    fetch_elections,
    record_export_run,
    row_to_record,
    sha256_file,
)
from civic.store import upsert, verify


def _row(conn, eid):
    return conn.execute("SELECT * FROM elections WHERE id = ?", (eid,)).fetchone()


def _force_status(conn, eid, status):
    """Move a record into a workflow status the audited transitions can't reach."""
    conn.execute("UPDATE elections SET status = ? WHERE id = ?", (status, eid))


class TestExportFields:
    def test_order_is_stable_and_carries_provenance(self):
        assert EXPORT_FIELDS[0] == "id"
        assert "jurisdiction_slug" in EXPORT_FIELDS
        assert "source_url" in EXPORT_FIELDS
        assert "verified_at" in EXPORT_FIELDS

    def test_db_bookkeeping_never_exported(self):
        # Consumers get substantive data, not our internal change-detection state.
        for internal in ("content_hash", "created_at", "updated_at"):
            assert internal not in EXPORT_FIELDS


class TestRowToRecord:
    def test_projects_only_the_export_fields(self, conn, make_record):
        eid = upsert(conn, make_record(offices=["Mayor", "Council"]), actor="t").election_id
        rec = row_to_record(_row(conn, eid))
        assert list(rec.keys()) == list(EXPORT_FIELDS)
        for internal in ("content_hash", "created_at", "updated_at"):
            assert internal not in rec

    def test_offices_decoded_from_json_to_a_list(self, conn, make_record):
        eid = upsert(conn, make_record(offices=["Mayor", "Council"]), actor="t").election_id
        rec = row_to_record(_row(conn, eid))
        assert rec["offices"] == ["Mayor", "Council"]
        assert isinstance(rec["offices"][0], str)

    def test_empty_offices_decode_to_an_empty_list(self, conn, make_record):
        # A NULL/blank column must not become None and crash a `.join()` downstream.
        eid = upsert(conn, make_record(offices=[]), actor="t").election_id
        conn.execute("UPDATE elections SET offices = '' WHERE id = ?", (eid,))
        assert row_to_record(_row(conn, eid))["offices"] == []

    def test_optional_fields_pass_through_as_none(self, conn, make_record):
        eid = upsert(conn, make_record(), actor="t").election_id
        rec = row_to_record(_row(conn, eid))
        assert rec["early_voting_end"] is None
        assert rec["verified_at"] is None

    def test_projection_is_stable_across_calls(self, conn, make_record):
        eid = upsert(conn, make_record(), actor="t").election_id
        assert row_to_record(_row(conn, eid)) == row_to_record(_row(conn, eid))


class TestFetchElections:
    def test_verified_only_by_default(self, conn, make_record):
        v = upsert(conn, make_record(jurisdiction_name="Verified Town"), actor="t")
        verify(conn, v.election_id, "curator")
        upsert(conn, make_record(jurisdiction_name="Draft Town"), actor="t")
        names = [row_to_record(r)["jurisdiction_name"] for r in fetch_elections(conn)]
        assert names == ["Verified Town"]

    def test_include_unverified_widens_to_staging_statuses(self, conn, make_record):
        v = upsert(conn, make_record(jurisdiction_name="Verified Town"), actor="t")
        verify(conn, v.election_id, "curator")
        upsert(conn, make_record(jurisdiction_name="Draft Town"), actor="t")
        upsert(conn, make_record(jurisdiction_name="Review Town"), actor="t")
        _force_status(conn, _one_id(conn, "Review Town"), "needs_review")
        names = sorted(
            row_to_record(r)["jurisdiction_name"] for r in fetch_elections(conn, True)
        )
        assert names == ["Draft Town", "Review Town", "Verified Town"]

    def test_superseded_and_cancelled_are_never_exported(self, conn, make_record):
        v = upsert(conn, make_record(jurisdiction_name="Live Town"), actor="t")
        verify(conn, v.election_id, "curator")
        for name, status in [("Old Town", "superseded"), ("Called Off", "cancelled")]:
            eid = upsert(conn, make_record(jurisdiction_name=name), actor="t").election_id
            _force_status(conn, eid, status)
        # Even with the widest selection, a retracted record must not ship.
        names = [
            row_to_record(r)["jurisdiction_name"] for r in fetch_elections(conn, True)
        ]
        assert names == ["Live Town"]

    def test_ordered_by_state_then_date_then_slug(self, conn, make_record):
        seeds = [
            ("VA", "2027-11-02", "Borough of Beta"),
            ("NJ", "2027-05-04", "Town of Alpha"),
            ("VA", "2027-05-04", "Town of Alpha"),
        ]
        for state, date, name in seeds:
            r = upsert(
                conn,
                make_record(state=state, election_date=date, jurisdiction_name=name),
                actor="t",
            )
            verify(conn, r.election_id, "curator")
        rows = fetch_elections(conn)
        assert [(r["state"], r["election_date"], r["jurisdiction_name"]) for r in rows] == [
            ("NJ", "2027-05-04", "Town of Alpha"),
            ("VA", "2027-05-04", "Town of Alpha"),
            ("VA", "2027-11-02", "Borough of Beta"),
        ]

    def test_empty_database(self, conn):
        assert fetch_elections(conn) == []


def _one_id(conn, name):
    return conn.execute(
        "SELECT id FROM elections WHERE jurisdiction_name = ?", (name,)
    ).fetchone()["id"]


class TestSha256File:
    def test_matches_the_documented_digest_of_empty_input(self, tmp_path):
        p = tmp_path / "empty.csv"
        p.write_bytes(b"")
        assert sha256_file(p) == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_known_content_digest(self, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_bytes(b"hello")
        assert sha256_file(p) == hashlib.sha256(b"hello").hexdigest()

    def test_large_file_read_across_chunk_boundaries(self, tmp_path):
        # The reader loops in 64 KiB chunks; a file larger than one chunk must
        # still hash correctly.
        payload = b"a" * (65536 * 2 + 1234)
        p = tmp_path / "big.csv"
        p.write_bytes(payload)
        assert sha256_file(p) == hashlib.sha256(payload).hexdigest()

    def test_changes_with_content(self, tmp_path):
        p = tmp_path / "f.txt"
        p.write_bytes(b"one")
        first = sha256_file(p)
        p.write_bytes(b"two")
        assert sha256_file(p) != first

    def test_binary_content_is_hashed_verbatim(self, tmp_path):
        payload = bytes(range(256))
        p = tmp_path / "bin.dat"
        p.write_bytes(payload)
        assert sha256_file(p) == hashlib.sha256(payload).hexdigest()


class TestRecordExportRun:
    def test_manifest_is_persisted_as_json(self, conn):
        manifest = [
            {"path": "csv/a.csv", "sha256": "a" * 64},
            {"path": "csv/CHANGELOG.md", "sha256": "b" * 64},
        ]
        record_export_run(conn, "2026.07.26", "csv", 3, manifest, "2026-07-26T00:00:00Z")
        row = conn.execute(
            "SELECT version, kind, record_count, file_manifest, created_at "
            "FROM export_runs"
        ).fetchone()
        assert row["version"] == "2026.07.26"
        assert row["kind"] == "csv"
        assert row["record_count"] == 3
        assert row["created_at"] == "2026-07-26T00:00:00Z"
        assert json.loads(row["file_manifest"]) == manifest

    def test_manifest_round_trips_unicode_paths(self, conn):
        manifest = [{"path": "ics/VA/town-of-é.ics", "sha256": "c" * 64}]
        record_export_run(conn, "2026.07.26", "ics", 1, manifest, "2026-07-26T00:00:00Z")
        stored = conn.execute("SELECT file_manifest FROM export_runs").fetchone()[0]
        assert json.loads(stored) == manifest


class TestHelperContract:
    def test_export_run_rejects_an_unknown_kind(self, conn):
        # The CHECK constraint is the guard against a typo'd exporter name.
        with pytest.raises(Exception):
            record_export_run(
                conn, "2026.07.26", "xlsx", 0, [], "2026-07-26T00:00:00Z"
            )
