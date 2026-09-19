"""Archived render support must not turn off the new-intake recency gate."""
import datetime as dt
import pytest
from pydantic import ValidationError
from civic.models import ElectionRecord


def record():
    return dict(state="CA", jurisdiction_type="state", jurisdiction_name="California",
                election_type="general", election_date=(dt.date.today() - dt.timedelta(days=60)).isoformat(),
                offices=["State assembly"], confidence="official", source_url="https://example.gov/elections",
                source_retrieved_at="2026-01-01T00:00:00Z", notes="Published election record")


def published(raw):
    # Establish a previously valid record without weakening production validation.
    recent = {**raw, "election_date": dt.date.today().isoformat()}
    prior = ElectionRecord(**recent).model_dump(mode="json")
    return {**prior, "election_date": raw["election_date"]}


def test_unchanged_published_archive_can_be_rendered():
    raw = record()
    assert ElectionRecord.model_validate(raw, context={"previously_published": published(raw)}).election_date.isoformat() == raw["election_date"]


def test_new_stale_intake_still_requires_historical_marker():
    with pytest.raises(ValidationError, match="more than 30 days"):
        ElectionRecord(**record())


@pytest.mark.parametrize("changes", [{"offices": ["Governor"]}, {"source_url": "https://example.gov/revised"}, {"notes": "Edited"}])
def test_changed_archive_still_requires_historical_review(changes):
    raw = record()
    with pytest.raises(ValidationError, match="more than 30 days"):
        ElectionRecord.model_validate({**raw, **changes}, context={"previously_published": published(raw)})


def test_archive_context_does_not_bypass_structural_validation():
    raw = record()
    with pytest.raises(ValidationError):
        ElectionRecord.model_validate({**raw, "state": "ZZ"}, context={"previously_published": published(raw)})
