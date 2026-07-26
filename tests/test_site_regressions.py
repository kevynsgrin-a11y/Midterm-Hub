"""Regressions for defects found in the frontend audit.

Each test names the failure it prevents. These are cheap invariants over the
rendered HTML — the expensive behavioural checks (contrast, hit targets, print,
no-JS) live in the Playwright suite, but everything checkable from a string is
checked here so a refactor can't quietly reintroduce it.
"""
from __future__ import annotations

import datetime
import re

import pytest

from civic.site.base import SiteConfig, safe_href
from civic.site.components import deadline_chip
from civic.site.data import Deadline


CFG = SiteConfig(origin="https://example.test")


class TestDeadlineSemantics:
    """`early_voting_start` opens a window; treating it like a closing deadline
    told voters early voting was over on the day it began."""

    def _chip(self, key, label, delta, today=None, window_end=None):
        today = today or datetime.date(2026, 7, 26)
        d = today + datetime.timedelta(days=delta)
        dl = Deadline(key=key, label=label, date=d, formatted="x")
        return deadline_chip(dl, today, window_end=window_end)

    def test_past_early_voting_start_is_open_not_closed(self):
        html = self._chip("early_voting_start", "Early voting begins", -1,
                          window_end=datetime.date(2026, 8, 10))
        assert "Open now" in html
        assert "deadline-chip--closed" not in html
        assert "(passed)" not in html

    def test_early_voting_after_window_end_is_closed(self):
        html = self._chip("early_voting_start", "Early voting begins", -20,
                          window_end=datetime.date(2026, 7, 20))
        assert "deadline-chip--closed" in html
        assert "Closed" in html

    def test_future_early_voting_start_says_opens(self):
        assert "Opens" in self._chip("early_voting_start", "Early voting begins", 10)

    def test_passed_registration_states_closed_in_words(self):
        html = self._chip("registration_deadline", "Voter registration deadline", -3)
        assert "Closed" in html, "status must be a word, not a strikethrough"

    def test_today_deadline_is_labelled(self):
        html = self._chip("registration_deadline", "Voter registration deadline", 0)
        assert "Today" in html
        assert "deadline-chip--today" in html

    def test_urgent_deadline_states_the_count(self):
        html = self._chip("registration_deadline", "Voter registration deadline", 3)
        assert "in 3 days" in html

    def test_chip_carries_machine_date_for_client_recompute(self):
        html = self._chip("registration_deadline", "Voter registration deadline", 5)
        assert 'data-deadline="2026-07-31"' in html
        assert "<time" in html and 'datetime="2026-07-31"' in html


class TestPlaceNaming:
    """Statewide records have jurisdiction_name == state_name, which produced
    "The Texas, Texas general election" on all 74 detail pages."""

    def test_place_phrase_collapses_statewide(self, make_view):
        e = make_view(jurisdiction_type="state", jurisdiction_name="Texas", state="TX")
        assert e.place_phrase == "Texas"

    def test_place_phrase_keeps_narrower_jurisdiction(self, make_view):
        e = make_view(jurisdiction_type="municipality",
                      jurisdiction_name="Town of Example", state="VA")
        assert e.place_phrase == "Town of Example, Virginia"


class TestCrumbs:
    def test_consecutive_duplicate_labels_collapse(self):
        from civic.site.pages import _crumbs

        got = _crumbs([("Home", "/"), ("States", "/states/"),
                       ("Texas", "/states/TX/"), ("Texas", "/elections/TX/texas/")])
        assert [label for label, _ in got] == ["Home", "States", "Texas"]
        # The shallower (canonical) URL is the one kept.
        assert got[-1][1] == "/states/TX/"

    def test_distinct_labels_are_untouched(self):
        from civic.site.pages import _crumbs

        items = [("Home", "/"), ("States", "/states/"), ("Virginia", "/states/VA/"),
                 ("Town of Example", "/elections/VA/town/")]
        assert _crumbs(items) == items


class TestSafeHref:
    @pytest.mark.parametrize("bad", [
        "javascript:alert(1)", " JaVaScRiPt:alert(1)", "data:text/html,<script>",
        "vbscript:x", "//evil.example/path",
    ])
    def test_hostile_schemes_are_defused(self, bad):
        assert safe_href(bad) == "#"

    @pytest.mark.parametrize("ok", [
        "https://sos.example.gov/calendar", "http://x.test/", "/states/TX/", "#anchor",
    ])
    def test_legitimate_urls_pass(self, ok):
        assert safe_href(ok) == ok


class TestCartogramBuckets:
    """Bucketing on count against max_count was degenerate: with a max of 2 only
    buckets 2 and 4 were reachable, so a five-swatch legend described a
    two-colour map."""

    def test_every_bucket_is_reachable(self):
        from civic.site.art import _urgency_bucket

        got = {_urgency_bucket(d) for d in (3, 20, 45, 90, 300, None)}
        assert got == {0, 1, 2, 3, 4}

    def test_sooner_dates_get_higher_buckets(self):
        from civic.site.art import _urgency_bucket

        assert _urgency_bucket(5) > _urgency_bucket(25) > _urgency_bucket(45)


class TestRenderedInvariants:
    """Whole-site invariants over the built HTML."""

    def test_no_place_name_stutter(self, built_site):
        offenders = [
            f for f, h in built_site.items()
            if re.search(r'content="[^"]*?\b([A-Z][\w ]+), \1\b', h)
        ]
        assert not offenders, offenders[:3]

    def test_no_duplicate_consecutive_breadcrumbs(self, built_site):
        offenders = []
        for f, h in built_site.items():
            m = re.search(r'<nav class="breadcrumb".*?</nav>', h, re.S)
            if not m:
                continue
            labels = re.findall(r"<li>(?:<a[^>]*>)?([^<]+)", m.group(0))
            if any(a.strip() == b.strip() for a, b in zip(labels, labels[1:])):
                offenders.append(f)
        assert not offenders, offenders[:3]

    def test_meta_descriptions_within_snippet_budget(self, built_site):
        import html as _h

        offenders = []
        for f, h in built_site.items():
            m = re.search(r'<meta name="description" content="(.*?)">', h, re.S)
            if m and len(_h.unescape(m.group(1))) > 160:
                offenders.append((f, len(_h.unescape(m.group(1)))))
        assert not offenders, offenders[:3]

    def test_subevents_carry_required_location(self, built_site):
        import json

        missing = 0
        for h in built_site.values():
            for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
                blk = json.loads(raw.replace("<\\/", "</"))
                for node in blk.get("@graph", [blk]):
                    if isinstance(node, dict):
                        for se in node.get("subEvent", []):
                            if "location" not in se:
                                missing += 1
        assert missing == 0

    def test_assets_are_content_hashed(self, built_site):
        home = built_site["index.html"]
        assert re.search(r'href="/assets/styles\.[0-9a-f]{8}\.css"', home)
        assert re.search(r'src="/assets/site\.[0-9a-f]{8}\.js"', home)

    def test_reveal_gate_is_owned_by_the_script_that_can_undo_it(self):
        """`html.js` is set by an inline head script that cannot fail; if the CSS
        hid content on that class and site.js never loaded, the page stayed blank."""
        from pathlib import Path

        css = Path("civic/site/assets/styles.css").read_text()
        js = Path("civic/site/assets/site.js").read_text()
        assert "html.js [data-reveal]" not in css
        assert "html.reveal-on [data-reveal]" in css
        assert 'classList.add("reveal-on")' in js

    def test_print_stylesheet_exists_and_beats_os_dark(self):
        from pathlib import Path

        css = Path("civic/site/assets/styles.css").read_text()
        assert "@media print" in css
        block = css[css.index("@media print"):]
        # Must match the OS-dark selector's specificity or it loses on the cascade.
        assert ":root:not([data-theme])" in block.split("}")[0] + block.split("{")[1]

    def test_no_strikethrough_on_dates(self):
        from pathlib import Path

        css = Path("civic/site/assets/styles.css").read_text()
        assert "line-through" not in css, "status must be carried by a word"
