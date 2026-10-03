"""Pure data mappers: deadline projection, row->record/export filtering, CSV value
normalization, intake dedupe, and the adapter registry.

These are the shape-and-validity mappers the rest of the pipeline trusts: they turn raw
rows/YAML into render-ready values and decide which records are exportable at all. The
tests below pin their known values plus the malformed, empty, and duplicate cases each
one is responsible for rejecting or collapsing.
"""
from __future__ import annotations

import datetime

import pytest

from civic.adapters import REGISTRY, StateAdapter, register
from civic.exports import EXPORT_FIELDS, fetch_elections, row_to_record
from civic.exports.csv_export import _row_values
from civic.intake import IntakeError, load_intake
from civic.site.data import Deadline, _build_deadlines
from civic.store import upsert, verify

TODAY = datetime.date(2027, 1, 1)


# --- civic/site/data.py: deadline projection -------------------------------


class TestBuildDeadlines:
    """Deadline rows are built only from the five known keys, then sorted by date."""

    def test_empty_record_yields_no_deadlines(self):
        assert _build_deadlines({}, TODAY) == []

    def test_known_values_and_sorting(self):
        got = _build_deadlines(
            {
                "early_voting_end": "2027-05-01",
                "registration_deadline": "2027-04-12",
                "candidate_filing_deadline": "2027-03-01",
                "early_voting_start": "2027-04-16",
            },
            TODAY,
        )
        # Chronological regardless of the order keys arrive in.
        assert [d.key for d in got] == [
            "candidate_filing_deadline",
            "registration_deadline",
            "early_voting_start",
            "early_voting_end",
        ]
        assert got[0].date == datetime.date(2027, 3, 1)
        # 'March 1, 2027' — fmt_short, not the compact month/day form.
        assert got[0].formatted == "March 1, 2027"
        assert got[0].label == "Candidate filing deadline"

    def test_registration_deadline_time_attached_only_to_registration(self):
        got = _build_deadlines(
            {
                "registration_deadline": "2027-04-12",
                "registration_deadline_time": "17:00",
                "early_voting_start": "2027-04-16",
            },
            TODAY,
        )
        times = {d.key: d.time for d in got}
        assert times["registration_deadline"] == "17:00"
        assert times["early_voting_start"] is None

    def test_missing_and_blank_dates_are_skipped(self):
        # None and "" both mean "not published" — neither may become a deadline.
        got = _build_deadlines(
            {"registration_deadline": "", "mail_ballot_request_deadline": None}, TODAY
        )
        assert got == []

    def test_unknown_key_is_ignored(self):
        assert _build_deadlines({"not_a_deadline": "2027-03-01"}, TODAY) == []

    def test_malformed_date_raises(self):
        with pytest.raises(ValueError):
            _build_deadlines({"registration_deadline": "2027-13-40"}, TODAY)


class TestDeadlineOpens:
    """Only a window-opening key may render as 'Open now'; a closing key never does."""

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("early_voting_start", True),
            ("early_voting_end", False),
            ("registration_deadline", False),
            ("candidate_filing_deadline", False),
            ("mail_ballot_request_deadline", False),
        ],
    )
    def test_opens_flag(self, key, expected):
        dl = Deadline(key=key, label="L", date=TODAY, formatted="Jan 1, 2027")
        assert dl.opens is expected


# --- civic/exports/__init__.py: row projection and status filtering --------


class TestRowToRecord:
    def test_keys_are_exactly_export_fields(self, conn, make_record):
        res = upsert(conn, make_record(), actor="t")
        row = conn.execute("SELECT * FROM elections WHERE id=?", (res.election_id,)).fetchone()
        assert set(row_to_record(row)) == set(EXPORT_FIELDS)

    def test_offices_json_decoded_to_list(self, conn, make_record):
        res = upsert(conn, make_record(offices=["Mayor", "Council"]), actor="t")
        row = conn.execute("SELECT * FROM elections WHERE id=?", (res.election_id,)).fetchone()
        assert row_to_record(row)["offices"] == ["Mayor", "Council"]

    def test_empty_offices_column_decodes_to_empty_list(self, conn, make_record):
        res = upsert(conn, make_record(offices=[]), actor="t")
        row = conn.execute("SELECT * FROM elections WHERE id=?", (res.election_id,)).fetchone()
        assert row_to_record(row)["offices"] == []

    def test_bookkeeping_fields_do_not_leak(self, conn, make_record):
        res = upsert(conn, make_record(), actor="t")
        row = conn.execute("SELECT * FROM elections WHERE id=?", (res.election_id,)).fetchone()
        rec = row_to_record(row)
        for hidden in ("content_hash", "created_at", "updated_at"):
            assert hidden not in rec


class TestFetchElections:
    def test_excludes_unverified_by_default(self, conn, make_record):
        upsert(conn, make_record(), actor="t")
        assert fetch_elections(conn) == []

    def test_includes_verified(self, conn, make_record):
        res = upsert(conn, make_record(), actor="t")
        verify(conn, res.election_id, "curator")
        assert len(fetch_elections(conn)) == 1

    def test_needs_review_requires_explicit_widening(self, conn, make_record):
        res = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="t")
        verify(conn, res.election_id, "curator")
        upsert(conn, make_record(registration_deadline="2027-04-15"), actor="t")
        assert fetch_elections(conn) == []
        assert len(fetch_elections(conn, include_unverified=True)) == 1

    @pytest.mark.parametrize("status", ["superseded", "cancelled"])
    def test_terminal_statuses_never_export(self, conn, make_record, status):
        res = upsert(conn, make_record(), actor="t")
        verify(conn, res.election_id, "curator")
        conn.execute(
            "UPDATE elections SET status=? WHERE id=?", (status, res.election_id)
        )
        # Even the widened selection must not carry a dead record.
        assert fetch_elections(conn, include_unverified=True) == []

    def test_empty_database_selects_nothing(self, conn):
        assert fetch_elections(conn) == []

    def test_sorted_by_state_then_date(self, conn, make_record):
        a = upsert(conn, make_record(jurisdiction_name="Alpha"), actor="t")
        b = upsert(conn, make_record(jurisdiction_name="Beta", state="NJ"), actor="t")
        c2 = upsert(
            conn, make_record(jurisdiction_name="Gamma", state="AK", election_date="2026-11-03"),
            actor="t",
        )
        for r in (a, b, c2):
            verify(conn, r.election_id, "curator")
        got = [(r["state"], r["election_date"]) for r in fetch_elections(conn)]
        assert got == sorted(got)
        assert [s for s, _ in got] == ["AK", "NJ", "VA"]


# --- civic/exports/csv_export.py: CSV value normalization ------------------


def _none_rec():
    return {
        k: None
        for k in (
            "id", "state", "jurisdiction_type", "jurisdiction_name", "election_date",
            "election_type", "registration_deadline", "early_voting_start",
            "early_voting_end", "mail_ballot_request_deadline",
            "candidate_filing_deadline", "confidence", "source_url", "verified_at",
        )
    }


class TestRowValues:
    def test_none_renders_as_empty_string_not_none(self):
        assert all(v == "" for v in _row_values({**_none_rec(), "offices": []}))

    def test_offices_semicolon_joined(self):
        rec = {**_none_rec(), "offices": ["Mayor", "Council"]}
        assert _row_values(rec)[6] == "Mayor;Council"

    def test_empty_offices_yields_empty_cell(self):
        assert _row_values({**_none_rec(), "offices": []})[6] == ""

    def test_single_office(self):
        assert _row_values({**_none_rec(), "offices": ["Mayor"]})[6] == "Mayor"

    def test_value_order_matches_csv_header(self, conn, make_record):
        from civic.exports.csv_export import CSV_HEADER

        res = upsert(conn, make_record(offices=["Mayor"]), actor="t")
        row = conn.execute("SELECT * FROM elections WHERE id=?", (res.election_id,)).fetchone()
        values = dict(zip(CSV_HEADER, _row_values(row_to_record(row))))
        # Each header column must land its own field — a shifted column would be
        # silently wrong in the B2B CSV.
        assert values["state"] == "VA"
        assert values["election_type"] == "municipal"
        assert values["offices"] == "Mayor"
        assert values["confidence"] == "official"
        assert values["verified_at"] == ""

    def test_offices_containing_separator_are_preserved(self, conn, make_record):
        res = upsert(conn, make_record(offices=["Clerk;Recorder"]), actor="t")
        row = conn.execute("SELECT * FROM elections WHERE id=?", (res.election_id,)).fetchone()
        assert _row_values(row_to_record(row))[6] == "Clerk;Recorder"


# --- civic/intake.py: dedupe and per-entry error indexing ------------------


def _entry(name, state="VA", jtype="municipality", etype="municipal",
           date="2027-05-04", slug=None):
    slug_line = f'  jurisdiction_slug: "{slug}"\n' if slug else ""
    return (
        f"- state: {state}\n  jurisdiction_type: {jtype}\n"
        f'  jurisdiction_name: "{name}"\n{slug_line}'
        f'  election_type: {etype}\n  election_date: "{date}"\n'
        f'  source_url: "https://x/1"\n'
    )


class TestIntakeDedupe:
    """A file may not name the same election twice; a distinct identity is fine."""

    def test_duplicate_name_rejected(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text(_entry("Alpha") + _entry("Alpha"), encoding="utf-8")
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        assert any("duplicate election" in e for e in exc.value.errors)

    def test_duplicate_error_names_first_offending_index(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text(_entry("Alpha") + _entry("Alpha"), encoding="utf-8")
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        (err,) = exc.value.errors
        assert "[entry 1]" in err and "as entry 0" in err

    def test_every_duplicate_reported(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text(_entry("Alpha") * 3, encoding="utf-8")
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        dups = [e for e in exc.value.errors if "duplicate election" in e]
        assert len(dups) == 2
        assert "[entry 1]" in dups[0] and "[entry 2]" in dups[1]

    def test_same_slug_different_type_is_distinct(self, tmp_path):
        # A county and a municipality sharing a slug have distinct identities.
        path = tmp_path / "i.yaml"
        path.write_text(
            _entry("Alpha", slug="shared") + _entry("Beta", jtype="county", slug="shared"),
            encoding="utf-8",
        )
        assert len(load_intake(path)) == 2

    def test_distinct_names_all_load(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text(_entry("Alpha") + _entry("Beta", state="NJ", date="2027-11-02"),
                        encoding="utf-8")
        assert len(load_intake(path)) == 2


class TestIntakeEntryErrors:
    def test_empty_list_is_valid(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text("[]", encoding="utf-8")
        assert load_intake(path) == []

    def test_non_mapping_entry_indexed(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text("- 5\n" + _entry("Alpha"), encoding="utf-8")
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        assert any("[entry 0]" in e and "must be a mapping" in e for e in exc.value.errors)

    def test_only_offending_entry_reported(self, tmp_path):
        # One bad entry among good ones: errors are per-entry, not whole-file noise.
        path = tmp_path / "i.yaml"
        path.write_text(
            _entry("Alpha")
            + _entry("Beta", state="ZZ", date="2027-11-02")
            + _entry("Gamma", state="NJ", date="2027-11-02"),
            encoding="utf-8",
        )
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        (err,) = exc.value.errors
        assert "[entry 1]" in err and "state" in err

    def test_multiple_bad_entries_all_indexed(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text(
            _entry("Alpha", state="ZZ") + _entry("Beta", date="not-a-date"),
            encoding="utf-8",
        )
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        assert any("[entry 0]" in e for e in exc.value.errors)
        assert any("[entry 1]" in e for e in exc.value.errors)

    def test_scalar_offices_rejected(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text(_entry("Alpha").replace(
            '  source_url', '  offices: "Mayor"\n  source_url'), encoding="utf-8")
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        assert any("offices" in e for e in exc.value.errors)

    def test_blank_file_rejected(self, tmp_path):
        path = tmp_path / "i.yaml"
        path.write_text("\n", encoding="utf-8")
        with pytest.raises(IntakeError) as exc:
            load_intake(path)
        assert any("empty" in e for e in exc.value.errors)


# --- civic/adapters/__init__.py: the adapter registry ----------------------


class _FakeAdapter:
    state = "VA"
    source_urls = ["https://sos.example.gov"]

    def parse(self, html, source_url):
        return []


@pytest.fixture()
def registry_guard():
    """Restore the module-level REGISTRY so registration cannot leak between tests."""
    saved = dict(REGISTRY)
    REGISTRY.clear()
    try:
        yield REGISTRY
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)


class TestAdapterRegistry:
    def test_registry_starts_empty(self, registry_guard):
        assert registry_guard == {}

    def test_register_returns_the_adapter(self, registry_guard):
        adapter = _FakeAdapter()
        assert register(adapter) is adapter

    def test_register_keys_on_lowercase_state(self, registry_guard):
        adapter = _FakeAdapter()
        register(adapter)
        assert list(registry_guard) == ["va"]
        assert registry_guard["va"] is adapter

    def test_state_is_normalized_to_lowercase(self, registry_guard):
        adapter = _FakeAdapter()
        adapter.state = "NJ"
        register(adapter)
        assert "nj" in registry_guard and "NJ" not in registry_guard

    def test_re_registering_replaces_by_key(self, registry_guard):
        first, second = _FakeAdapter(), _FakeAdapter()
        register(first)
        register(second)
        assert len(registry_guard) == 1
        assert registry_guard["va"] is second

    def test_distinct_states_coexist(self, registry_guard):
        va, nj = _FakeAdapter(), _FakeAdapter()
        nj.state = "NJ"
        register(va)
        register(nj)
        assert set(registry_guard) == {"va", "nj"}

    def test_adapter_satisfies_the_protocol(self):
        assert isinstance(_FakeAdapter(), StateAdapter)

    def test_object_without_parse_is_not_an_adapter(self):
        class NotAnAdapter:
            state = "VA"
            source_urls: list = []

        assert not isinstance(NotAnAdapter(), StateAdapter)
