"""ID determinism, slugify edge cases, and content-hash stability."""
from __future__ import annotations

from civic.ids import content_hash, election_id, slugify


class TestSlugify:
    def test_lowercases_and_hyphenates(self):
        assert slugify("Town of Example") == "town-of-example"

    def test_strips_accents(self):
        assert slugify("Cañon City") == "canon-city"
        assert slugify("Doña Ana County") == "dona-ana-county"

    def test_collapses_repeated_separators(self):
        assert slugify("A -- B __ C") == "a-b-c"
        assert slugify("St. Mary's / West") == "st-mary-s-west"

    def test_strips_leading_and_trailing_hyphens(self):
        assert slugify("--Hello, World!--") == "hello-world"

    def test_punctuation_only_becomes_empty(self):
        assert slugify("!!!") == ""

    def test_numbers_preserved(self):
        assert slugify("Ward 3 (District 12)") == "ward-3-district-12"


class TestElectionId:
    def test_deterministic(self):
        a = election_id("VA", "town-of-example", "2027-05-04", "municipal")
        b = election_id("VA", "town-of-example", "2027-05-04", "municipal")
        assert a == b
        assert len(a) == 16
        assert all(ch in "0123456789abcdef" for ch in a)

    def test_state_case_insensitive(self):
        assert election_id("va", "x", "2027-05-04", "municipal") == election_id(
            "VA", "x", "2027-05-04", "municipal"
        )

    def test_distinct_inputs_differ(self):
        base = election_id("VA", "town-of-example", "2027-05-04", "municipal")
        assert base != election_id("NJ", "town-of-example", "2027-05-04", "municipal")
        assert base != election_id("VA", "other-town", "2027-05-04", "municipal")
        assert base != election_id("VA", "town-of-example", "2027-11-02", "municipal")
        assert base != election_id("VA", "town-of-example", "2027-05-04", "special")


def _record(**over):
    base = {
        "state": "VA",
        "jurisdiction_type": "municipality",
        "jurisdiction_name": "Town of Example",
        "jurisdiction_slug": "town-of-example",
        "election_date": "2027-05-04",
        "election_type": "municipal",
        "offices": ["Mayor", "Council"],
        "registration_deadline": "2027-04-12",
        "registration_deadline_time": None,
        "early_voting_start": None,
        "early_voting_end": None,
        "mail_ballot_request_deadline": None,
        "candidate_filing_deadline": None,
        "timezone": "America/New_York",
        "confidence": "official",
    }
    base.update(over)
    return base


class TestContentHash:
    def test_stable_under_key_reordering(self):
        d1 = _record()
        d2 = dict(reversed(list(d1.items())))
        assert content_hash(d1) == content_hash(d2)

    def test_insensitive_to_excluded_fields(self):
        substantive = _record()
        with_extra = _record()
        with_extra.update(
            {
                "status": "verified",
                "source_url": "https://elsewhere.example",
                "source_retrieved_at": "2026-01-01T00:00:00Z",
                "verified_by": "someone",
                "notes": "totally different notes",
                "created_at": "2026-01-01T00:00:00Z",
            }
        )
        assert content_hash(substantive) == content_hash(with_extra)

    def test_changes_with_substantive_field(self):
        base = content_hash(_record())
        assert base != content_hash(_record(election_date="2027-05-05"))
        assert base != content_hash(_record(offices=["Mayor"]))
        assert base != content_hash(_record(confidence="secondary"))

    def test_offices_order_matters(self):
        # Office order is meaningful data, not incidental.
        assert content_hash(_record(offices=["A", "B"])) != content_hash(
            _record(offices=["B", "A"])
        )
