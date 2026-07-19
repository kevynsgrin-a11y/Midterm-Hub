"""Exports: CSV header golden test, JSON shape, ICS round-trip, verified-only
filtering, and export_runs manifest recording."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from icalendar import Calendar

from civic.exports.csv_export import CSV_HEADER, export_csv
from civic.exports.ics_export import export_ics
from civic.exports.json_export import export_json
from civic.store import upsert, verify

# The exact, byte-for-byte header the B2B CSV must emit.
GOLDEN_HEADER = (
    "id,state,jurisdiction_type,jurisdiction_name,election_date,election_type,offices,"
    "registration_deadline,early_voting_start,early_voting_end,"
    "mail_ballot_request_deadline,candidate_filing_deadline,confidence,source_url,"
    "verified_at"
)

GEN_AT = "2026-07-19T00:00:00Z"
GEN_AT_DT = datetime.datetime(2026, 7, 19, tzinfo=datetime.timezone.utc)
VERSION = "2026.07.19"


def _seed(conn, make_record):
    """One verified record and one unverified record in different jurisdictions."""
    v = upsert(
        conn,
        make_record(
            jurisdiction_name="Town of Example",
            registration_deadline="2027-04-12",
            offices=["Mayor", "Council"],
        ),
        actor="t",
    )
    verify(conn, v.election_id, "curator")
    u = upsert(
        conn,
        make_record(jurisdiction_name="Borough of Placeholder", state="NJ"),
        actor="t",
    )
    return v.election_id, u.election_id


class TestCsv:
    def test_header_matches_spec_byte_for_byte(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_csv(conn, tmp_path, VERSION, GEN_AT)
        csv_path = tmp_path / "csv" / VERSION / f"off_cycle_elections_{VERSION}.csv"
        first_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == GOLDEN_HEADER
        assert ",".join(CSV_HEADER) == GOLDEN_HEADER

    def test_offices_semicolon_joined(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_csv(conn, tmp_path, VERSION, GEN_AT)
        csv_path = tmp_path / "csv" / VERSION / f"off_cycle_elections_{VERSION}.csv"
        body = csv_path.read_text(encoding="utf-8").splitlines()
        # Only the verified record is present by default.
        assert len(body) == 2
        assert "Mayor;Council" in body[1]

    def test_changelog_written(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_csv(conn, tmp_path, VERSION, GEN_AT)
        changelog = tmp_path / "csv" / VERSION / "CHANGELOG.md"
        assert changelog.exists()
        assert "Changelog" in changelog.read_text(encoding="utf-8")


class TestJson:
    def test_top_level_shape(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_json(conn, tmp_path, VERSION, GEN_AT)
        index = tmp_path / "json" / "VA" / "index.json"
        payload = json.loads(index.read_text(encoding="utf-8"))
        assert set(payload.keys()) == {
            "generated_at",
            "version",
            "state",
            "includes_unverified",
            "elections",
        }
        assert payload["state"] == "VA"
        assert payload["version"] == VERSION
        assert payload["includes_unverified"] is False
        assert isinstance(payload["elections"], list)
        assert payload["elections"][0]["jurisdiction_name"] == "Town of Example"
        # Offices decoded back to a list; no DB bookkeeping fields leak.
        assert payload["elections"][0]["offices"] == ["Mayor", "Council"]
        assert "content_hash" not in payload["elections"][0]

    def test_per_jurisdiction_file(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_json(conn, tmp_path, VERSION, GEN_AT)
        juris = tmp_path / "json" / "VA" / "town-of-example.json"
        assert juris.exists()
        payload = json.loads(juris.read_text(encoding="utf-8"))
        assert all(e["jurisdiction_slug"] == "town-of-example" for e in payload["elections"])


class TestVerifiedOnlyFiltering:
    def test_default_excludes_unverified(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_json(conn, tmp_path, VERSION, GEN_AT)
        # NJ record is unverified → no NJ output at all by default.
        assert not (tmp_path / "json" / "NJ").exists()
        va = json.loads((tmp_path / "json" / "VA" / "index.json").read_text())
        assert len(va["elections"]) == 1

    def test_include_unverified_widens_and_stamps(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_json(conn, tmp_path, VERSION, GEN_AT, include_unverified=True)
        nj = json.loads((tmp_path / "json" / "NJ" / "index.json").read_text())
        assert nj["includes_unverified"] is True
        assert len(nj["elections"]) == 1


class TestIcs:
    def test_round_trips(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_ics(
            conn, tmp_path, VERSION, GEN_AT, GEN_AT_DT, "civic-calendar.local"
        )
        ics_path = tmp_path / "ics" / "VA" / "town-of-example.ics"
        assert ics_path.exists()
        cal = Calendar.from_ical(ics_path.read_bytes())
        events = [c for c in cal.walk() if c.name == "VEVENT"]
        # Election event + registration-deadline event.
        assert len(events) == 2
        uids = {str(e["UID"]) for e in events}
        assert any(uid.endswith("@civic-calendar.local") for uid in uids)
        assert any(uid.endswith("-reg@civic-calendar.local") for uid in uids)

    def test_summary_and_all_day(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_ics(conn, tmp_path, VERSION, GEN_AT, GEN_AT_DT, "civic-calendar.local")
        cal = Calendar.from_ical(
            (tmp_path / "ics" / "VA" / "town-of-example.ics").read_bytes()
        )
        election_ev = next(
            e
            for e in cal.walk()
            if e.name == "VEVENT" and "election" in str(e["SUMMARY"])
        )
        assert "Town of Example" in str(election_ev["SUMMARY"])
        # All-day event: DTSTART is a date value.
        assert isinstance(election_ev.decoded("DTSTART"), datetime.date)


class TestExportRuns:
    def test_manifest_recorded_for_each_kind(self, conn, make_record, tmp_path):
        _seed(conn, make_record)
        export_json(conn, tmp_path, VERSION, GEN_AT)
        export_csv(conn, tmp_path, VERSION, GEN_AT)
        export_ics(conn, tmp_path, VERSION, GEN_AT, GEN_AT_DT, "civic-calendar.local")

        rows = conn.execute(
            "SELECT kind, record_count, file_manifest FROM export_runs ORDER BY kind"
        ).fetchall()
        kinds = {r["kind"] for r in rows}
        assert kinds == {"csv", "ics", "json"}
        for r in rows:
            manifest = json.loads(r["file_manifest"])
            assert isinstance(manifest, list)
            for entry in manifest:
                assert set(entry.keys()) == {"path", "sha256"}
                assert len(entry["sha256"]) == 64
