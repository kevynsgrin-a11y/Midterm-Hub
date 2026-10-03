"""Derived view-model properties in civic.site.data.

These properties drive countdown copy, urgency flags, and deadline ordering on
every page. The interesting cases are the boundaries: "today", the day after, a
window with no end date, and the closes-vs-opens distinction that decides whether
a past date reads as "missed it" or "it's happening now".
"""
from __future__ import annotations

import datetime

from civic.site.data import (
    DEADLINE_CLOSES,
    DEADLINE_OPENS,
    Deadline,
    fmt_compact,
    fmt_full,
    fmt_short,
)

TODAY = datetime.date(2026, 7, 26)


def _dl(key, date, time=None):
    return Deadline(
        key=key, label=key.replace("_", " ").title(), date=date,
        formatted=fmt_short(date), time=time,
    )


class TestFormatters:
    def test_full_includes_weekday_and_year(self):
        assert fmt_full(datetime.date(2027, 5, 4)) == "Tuesday, May 4, 2027"

    def test_short_drops_weekday(self):
        assert fmt_short(datetime.date(2027, 5, 4)) == "May 4, 2027"

    def test_compact_drops_year(self):
        assert fmt_compact(datetime.date(2027, 5, 4)) == "May 4"

    def test_single_digit_day_is_never_zero_padded(self):
        # The reason these helpers exist: "%-d" is not portable (Windows), and a
        # zero-padded "May 04" reads as a machine-generated date.
        for fn in (fmt_full, fmt_short, fmt_compact):
            assert "05" not in fn(datetime.date(2027, 5, 4))
        assert fmt_full(datetime.date(2027, 12, 25)) == "Saturday, December 25, 2027"

    def test_leap_day(self):
        assert fmt_full(datetime.date(2028, 2, 29)) == "Tuesday, February 29, 2028"


class TestDeadlineSemantics:
    def test_early_voting_start_opens_a_window(self):
        assert _dl("early_voting_start", TODAY).opens is True
        assert "early_voting_start" in DEADLINE_OPENS

    def test_closing_deadlines_do_not_open(self):
        assert "early_voting_start" not in DEADLINE_CLOSES
        for key in sorted(DEADLINE_CLOSES):
            assert _dl(key, TODAY).opens is False


class TestUrls:
    def test_derived_from_state_slug_and_id(self, make_view):
        e = make_view()
        assert e.url == f"/elections/VA/town-of-example/{'a' * 16}/"
        assert e.jurisdiction_url == "/elections/VA/town-of-example/"
        assert e.state_url == "/states/VA/"

    def test_disambiguated_url_slug_overrides_jurisdiction_slug(self, make_view):
        # A same-slug/different-type collision within a state gets its own URL.
        e = make_view(jurisdiction_type="county", url_slug="town-of-example-county")
        assert e.jurisdiction_slug == "town-of-example"
        assert e.url == f"/elections/VA/town-of-example-county/{'a' * 16}/"
        assert e.jurisdiction_url == "/elections/VA/town-of-example-county/"

    def test_title(self, make_view):
        assert make_view().title == "Town of Example Municipal Election"


class TestDates:
    def test_date_properties_delegate_to_formatters(self, make_view):
        e = make_view(election_date=datetime.date(2026, 11, 3))
        assert e.date_full == "Tuesday, November 3, 2026"
        assert e.date_short == "November 3, 2026"
        assert e.date_iso == "2026-11-03"
        assert e.date_compact == "Nov 3"

    def test_days_until_is_signed(self, make_view):
        assert make_view(
            election_date=TODAY + datetime.timedelta(days=70)
        ).days_until == 70
        assert make_view(
            election_date=TODAY - datetime.timedelta(days=3)
        ).days_until == -3

    def test_today_counts_as_upcoming(self, make_view):
        # Election day itself is still ahead of the voter.
        e = make_view(election_date=TODAY)
        assert e.is_upcoming is True
        assert e.days_until == 0

    def test_yesterday_is_not_upcoming(self, make_view):
        assert make_view(
            election_date=TODAY - datetime.timedelta(days=1)
        ).is_upcoming is False


class TestCountdown:
    def _countdown(self, make_view, delta):
        return make_view(election_date=TODAY + datetime.timedelta(days=delta)).countdown

    def test_named_days(self, make_view):
        assert self._countdown(make_view, 0) == "Today"
        assert self._countdown(make_view, 1) == "Tomorrow"
        assert self._countdown(make_view, -1) == "Yesterday"

    def test_counts(self, make_view):
        assert self._countdown(make_view, 2) == "in 2 days"
        assert self._countdown(make_view, 45) == "in 45 days"
        assert self._countdown(make_view, -2) == "2 days ago"
        assert self._countdown(make_view, -30) == "30 days ago"

    def test_never_leaks_a_sign_into_the_copy(self, make_view):
        # "-1 days" style output would read as a bug to a voter.
        for delta in (-5, -1, 0, 1, 5):
            assert "-" not in self._countdown(make_view, delta)


class TestOfficesAndPlace:
    def test_offices_summary_joins_with_commas(self, make_view):
        assert make_view(offices=["Mayor", "Council"]).offices_summary == "Mayor, Council"

    def test_offices_summary_empty_when_no_offices(self, make_view):
        assert make_view(offices=[]).offices_summary == ""

    def test_statewide_record_does_not_stutter(self, make_view):
        e = make_view(jurisdiction_type="state", jurisdiction_name="Virginia")
        assert e.place_phrase == "Virginia"
        assert e.is_statewide is True

    def test_narrower_jurisdiction_keeps_both_names(self, make_view):
        e = make_view(jurisdiction_type="municipality")
        assert e.place_phrase == "Town of Example, Virginia"
        assert e.is_statewide is False

    def test_same_name_as_state_is_treated_as_statewide(self, make_view):
        # Even if typed as a county, a jurisdiction named after its state reads
        # correctly without a duplicated name.
        e = make_view(jurisdiction_type="county", jurisdiction_name="Virginia")
        assert e.place_phrase == "Virginia"
        assert e.is_statewide is True


class TestEarlyVoting:
    def _view(self, make_view, start, end):
        deadlines = []
        if start is not None:
            deadlines.append(_dl("early_voting_start", start))
        if end is not None:
            deadlines.append(_dl("early_voting_end", end))
        return make_view(deadlines=deadlines)

    def test_closed_before_the_window_opens(self, make_view):
        e = self._view(
            make_view, TODAY + datetime.timedelta(days=1),
            TODAY + datetime.timedelta(days=10),
        )
        assert e.early_voting_open is False

    def test_open_on_the_first_day(self, make_view):
        e = self._view(
            make_view, TODAY, TODAY + datetime.timedelta(days=10)
        )
        assert e.early_voting_open is True

    def test_open_on_the_last_day(self, make_view):
        e = self._view(
            make_view, TODAY - datetime.timedelta(days=10), TODAY
        )
        assert e.early_voting_open is True

    def test_closed_the_day_after_the_window_ends(self, make_view):
        e = self._view(
            make_view, TODAY - datetime.timedelta(days=11),
            TODAY - datetime.timedelta(days=1),
        )
        assert e.early_voting_open is False

    def test_open_with_no_end_date_recorded(self, make_view):
        # An unclosed window stays open rather than silently reporting "closed".
        e = self._view(make_view, TODAY - datetime.timedelta(days=1), None)
        assert e.early_voting_open is True

    def test_closed_with_no_start_date_recorded(self, make_view):
        assert self._view(make_view, None, None).early_voting_open is False
        assert self._view(make_view, None, TODAY).early_voting_open is False

    def test_end_date_property(self, make_view):
        end = TODAY + datetime.timedelta(days=10)
        assert self._view(make_view, TODAY, end).early_voting_end_date == end
        assert self._view(make_view, TODAY, None).early_voting_end_date is None


class TestRegistration:
    def test_closed_once_the_deadline_has_passed(self, make_view):
        e = make_view(
            election_date=TODAY + datetime.timedelta(days=30),
            deadlines=[_dl("registration_deadline", TODAY - datetime.timedelta(days=1))],
        )
        assert e.registration_closed is True

    def test_still_open_on_the_deadline_itself(self, make_view):
        e = make_view(
            election_date=TODAY + datetime.timedelta(days=30),
            deadlines=[_dl("registration_deadline", TODAY)],
        )
        assert e.registration_closed is False

    def test_not_closed_once_the_election_is_over(self, make_view):
        # A past election is not "registration closed" — the race is simply done.
        e = make_view(
            election_date=TODAY - datetime.timedelta(days=5),
            deadlines=[_dl("registration_deadline", TODAY - datetime.timedelta(days=20))],
        )
        assert e.registration_closed is False

    def test_no_deadline_recorded(self, make_view):
        assert make_view(deadlines=[]).registration_closed is False
        assert make_view(deadlines=[]).registration_deadline_formatted is None

    def test_formatted_deadline_surfaces_the_label(self, make_view):
        e = make_view(
            deadlines=[_dl("registration_deadline", datetime.date(2026, 10, 5))]
        )
        assert e.registration_deadline_formatted == "October 5, 2026"


class TestNextDeadline:
    def test_picks_the_soonest_date_still_ahead(self, make_view):
        e = make_view(
            deadlines=[
                _dl("candidate_filing_deadline", datetime.date(2026, 3, 1)),
                _dl("registration_deadline", datetime.date(2026, 10, 5)),
                _dl("early_voting_start", datetime.date(2026, 10, 19)),
            ]
        )
        assert e.next_deadline.key == "registration_deadline"

    def test_a_deadline_today_still_counts(self, make_view):
        e = make_view(
            deadlines=[
                _dl("registration_deadline", TODAY - datetime.timedelta(days=1)),
                _dl("early_voting_start", TODAY),
            ]
        )
        assert e.next_deadline.key == "early_voting_start"

    def test_none_when_every_deadline_has_passed(self, make_view):
        e = make_view(
            deadlines=[_dl("registration_deadline", TODAY - datetime.timedelta(days=1))]
        )
        assert e.next_deadline is None

    def test_none_when_there_are_no_deadlines(self, make_view):
        assert make_view(deadlines=[]).next_deadline is None
