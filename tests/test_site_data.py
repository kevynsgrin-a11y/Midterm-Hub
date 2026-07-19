"""View-model layer: grouping, derived fields, URLs, deadline ordering."""
from __future__ import annotations

import datetime

from civic.site.data import load_site_data
from civic.store import upsert, verify

TODAY = datetime.date(2027, 1, 1)


def _seed(conn, make_record):
    a = upsert(
        conn,
        make_record(
            jurisdiction_name="Town of Example",
            election_date="2027-05-04",
            registration_deadline="2027-04-12",
            early_voting_start="2027-04-16",
            early_voting_end="2027-05-01",
            candidate_filing_deadline="2027-03-01",
        ),
        actor="t",
    )
    verify(conn, a.election_id, "curator")
    b = upsert(
        conn,
        make_record(
            jurisdiction_name="Borough of Placeholder",
            state="NJ",
            election_date="2027-11-02",
            registration_deadline="2027-10-12",
        ),
        actor="t",
    )
    verify(conn, b.election_id, "curator")
    # An unverified record must not appear on the site.
    upsert(conn, make_record(jurisdiction_name="Hidden Town", election_date="2027-06-01"), actor="t")
    return a.election_id, b.election_id


def _data(conn):
    return load_site_data(
        conn, version="2027.01.01", generated_at="2027-01-01T00:00:00Z", today=TODAY
    )


class TestGrouping:
    def test_only_verified_included(self, conn, make_record):
        _seed(conn, make_record)
        d = _data(conn)
        names = {e.jurisdiction_name for e in d.elections}
        assert "Hidden Town" not in names
        assert d.total_elections == 2

    def test_states_and_jurisdictions(self, conn, make_record):
        _seed(conn, make_record)
        d = _data(conn)
        assert d.total_states == 2
        assert {s.code for s in d.states} == {"VA", "NJ"}
        # Sorted by full state name: New Jersey before Virginia.
        assert [s.code for s in d.states] == ["NJ", "VA"]
        assert d.total_jurisdictions == 2

    def test_state_view_counts(self, conn, make_record):
        _seed(conn, make_record)
        d = _data(conn)
        va = next(s for s in d.states if s.code == "VA")
        assert va.name == "Virginia"
        assert va.election_count == 1
        assert va.jurisdiction_count == 1


class TestDerived:
    def test_urls(self, conn, make_record):
        eid, _ = _seed(conn, make_record)
        d = _data(conn)
        e = next(e for e in d.elections if e.id == eid)
        assert e.url == f"/elections/VA/town-of-example/{eid}/"
        assert e.jurisdiction_url == "/elections/VA/town-of-example/"
        assert e.state_url == "/states/VA/"

    def test_labels_and_formatting(self, conn, make_record):
        eid, _ = _seed(conn, make_record)
        d = _data(conn)
        e = next(e for e in d.elections if e.id == eid)
        assert e.state_name == "Virginia"
        assert e.election_type_label == "Municipal"
        assert e.date_full == "Tuesday, May 4, 2027"
        assert e.date_iso == "2027-05-04"

    def test_countdown(self, conn, make_record):
        eid, _ = _seed(conn, make_record)
        d = _data(conn)
        e = next(e for e in d.elections if e.id == eid)
        assert e.is_upcoming is True
        assert e.days_until == (datetime.date(2027, 5, 4) - TODAY).days
        assert "days" in e.countdown

    def test_deadlines_sorted_by_date(self, conn, make_record):
        eid, _ = _seed(conn, make_record)
        d = _data(conn)
        e = next(e for e in d.elections if e.id == eid)
        dates = [dl.date for dl in e.deadlines]
        assert dates == sorted(dates)
        # Candidate filing (Mar 1) is the earliest key date present.
        assert e.deadlines[0].key == "candidate_filing_deadline"
        labels = {dl.key for dl in e.deadlines}
        assert {"registration_deadline", "early_voting_start", "early_voting_end"} <= labels


class TestSiteMeta:
    def test_last_modified_uses_verified_at(self, conn, make_record):
        _seed(conn, make_record)
        d = _data(conn)
        assert d.last_modified >= d.generated_at or d.last_modified is not None
        assert d.type_counts.get("municipal", 0) >= 1
