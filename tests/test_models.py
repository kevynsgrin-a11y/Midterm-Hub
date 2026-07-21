"""Model validation: strict dates, state whitelist, warnings vs. hard failures,
historical backfill, slug auto-derivation."""
from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from civic.models import ElectionRecord


def _valid(**over):
    base = {
        "state": "VA",
        "jurisdiction_type": "municipality",
        "jurisdiction_name": "Town of Example",
        "election_type": "municipal",
        "election_date": "2027-05-04",
        "source_url": "https://elections.example.gov/x",
    }
    base.update(over)
    return ElectionRecord(**base)


class TestStateWhitelist:
    def test_accepts_known_state_and_uppercases(self):
        assert _valid(state="va").state == "VA"

    def test_accepts_dc(self):
        assert _valid(state="DC").state == "DC"

    def test_rejects_unknown(self):
        with pytest.raises(ValidationError):
            _valid(state="ZZ")

    def test_rejects_non_two_letter(self):
        with pytest.raises(ValidationError):
            _valid(state="Virginia")


class TestStrictDates:
    def test_accepts_iso_date(self):
        assert _valid(election_date="2027-05-04").election_date == datetime.date(2027, 5, 4)

    def test_accepts_date_object(self):
        assert _valid(election_date=datetime.date(2027, 5, 4)).election_date == datetime.date(
            2027, 5, 4
        )

    def test_rejects_non_iso_string(self):
        with pytest.raises(ValidationError):
            _valid(election_date="05/04/2027")

    def test_rejects_invalid_calendar_date(self):
        with pytest.raises(ValidationError):
            _valid(election_date="2027-13-40")

    def test_rejects_datetime_for_civil_date(self):
        with pytest.raises(ValidationError):
            _valid(election_date=datetime.datetime(2027, 5, 4, 12, 0))


class TestRegistrationTime:
    def test_accepts_hhmm(self):
        assert _valid(registration_deadline_time="17:00").registration_deadline_time == "17:00"

    def test_rejects_bad_format(self):
        with pytest.raises(ValidationError):
            _valid(registration_deadline_time="5pm")

    def test_rejects_impossible_clock_time(self):
        with pytest.raises(ValidationError):
            _valid(registration_deadline_time="25:99")


class TestStricterValidation:
    def test_rejects_iso_week_and_basic_dates(self):
        for bad in ("2027-W44-2", "20271102"):
            with pytest.raises(ValidationError):
                _valid(election_date=bad)

    def test_rejects_whitespace_jurisdiction_name(self):
        with pytest.raises(ValidationError):
            _valid(jurisdiction_name="   ")

    def test_historical_requires_whole_word(self):
        import datetime as _dt

        old = (_dt.date.today() - _dt.timedelta(days=400)).isoformat()
        # 'prehistorical' must NOT disarm the staleness guard.
        with pytest.raises(ValidationError):
            _valid(election_date=old, notes="near a prehistorical dig site")
        # whole-word 'historical' does.
        assert _valid(election_date=old, notes="historical backfill").election_date.isoformat() == old


class TestOffices:
    def test_rejects_empty_string_office(self):
        with pytest.raises(ValidationError):
            _valid(offices=["Mayor", ""])

    def test_accepts_list_of_strings(self):
        assert _valid(offices=["Mayor", "Council"]).offices == ["Mayor", "Council"]


class TestOrderingWarnings:
    def test_registration_after_election_is_warning_not_error(self):
        rec = _valid(election_date="2027-05-04", registration_deadline="2027-05-10")
        assert rec.warnings  # collected, not raised
        assert any("registration_deadline" in w for w in rec.warnings)

    def test_filing_deadline_not_before_election_warns(self):
        rec = _valid(election_date="2027-05-04", candidate_filing_deadline="2027-05-04")
        assert any("candidate_filing_deadline" in w for w in rec.warnings)

    def test_early_voting_window_warns(self):
        rec = _valid(
            election_date="2027-05-04",
            early_voting_start="2027-05-02",
            early_voting_end="2027-05-01",
        )
        assert any("early_voting" in w for w in rec.warnings)

    def test_clean_record_has_no_warnings(self):
        rec = _valid(
            election_date="2027-05-04",
            registration_deadline="2027-04-12",
            early_voting_start="2027-04-16",
            early_voting_end="2027-05-01",
            candidate_filing_deadline="2027-03-01",
        )
        assert rec.warnings == []

    def test_warnings_excluded_from_serialization(self):
        rec = _valid(election_date="2027-05-04", registration_deadline="2027-05-10")
        assert "warnings" not in rec.model_dump()


class TestRecencyHardFailure:
    def test_stale_date_without_historical_fails(self):
        old = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
        with pytest.raises(ValidationError):
            _valid(election_date=old)

    def test_stale_date_with_historical_note_allowed(self):
        old = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
        rec = _valid(election_date=old, notes="historical backfill from archive")
        assert rec.election_date.isoformat() == old

    def test_within_30_days_past_allowed(self):
        recent = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
        rec = _valid(election_date=recent)
        assert rec.election_date.isoformat() == recent


class TestSlugDerivation:
    def test_auto_derives_when_absent(self):
        assert _valid(jurisdiction_name="Town of Example").jurisdiction_slug == "town-of-example"

    def test_respects_explicit_slug(self):
        rec = _valid(jurisdiction_name="Town of Example", jurisdiction_slug="custom-slug")
        assert rec.jurisdiction_slug == "custom-slug"


class TestExtraForbidden:
    def test_unknown_field_rejected(self):
        with pytest.raises(ValidationError):
            _valid(bogus_field="nope")
