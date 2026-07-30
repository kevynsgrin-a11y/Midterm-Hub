"""Shared pytest fixtures and record factory."""
from __future__ import annotations

import sqlite3
from typing import Any, Callable

import pytest

from civic.db import connect
from civic.models import ElectionRecord


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """Fresh in-memory database with the schema applied."""
    c = connect(":memory:")
    try:
        yield c
    finally:
        c.close()


_BASE: dict[str, Any] = {
    "state": "VA",
    "jurisdiction_type": "municipality",
    "jurisdiction_name": "Town of Example",
    "election_type": "municipal",
    "election_date": "2027-05-04",
    "offices": ["Mayor"],
    "registration_deadline": "2027-04-12",
    "confidence": "official",
    "source_url": "https://elections.example.gov/town-of-example-2027",
    "notes": "illustrative placeholder",
}


@pytest.fixture()
def make_record() -> Callable[..., ElectionRecord]:
    """Return a factory producing valid future-dated ElectionRecords."""

    def _factory(**overrides: Any) -> ElectionRecord:
        data = {**_BASE, **overrides}
        return ElectionRecord(**data)

    return _factory


@pytest.fixture()
def make_view() -> Callable[..., Any]:
    """An ElectionView built directly, for view-layer property tests."""
    import datetime

    from civic.site.data import (
        ELECTION_TYPE_LABELS,
        JURISDICTION_TYPE_LABELS,
        STATE_NAMES,
        ElectionView,
    )

    def _factory(**overrides: Any):
        state = overrides.pop("state", "VA")
        jtype = overrides.pop("jurisdiction_type", "municipality")
        etype = overrides.pop("election_type", "municipal")
        base = dict(
            id="a" * 16,
            state=state,
            state_name=STATE_NAMES.get(state, state),
            jurisdiction_type=jtype,
            jurisdiction_type_label=JURISDICTION_TYPE_LABELS.get(jtype, jtype),
            jurisdiction_name=overrides.pop("jurisdiction_name", "Town of Example"),
            jurisdiction_slug="town-of-example",
            election_date=datetime.date(2026, 11, 3),
            election_type=etype,
            election_type_label=ELECTION_TYPE_LABELS.get(etype, etype),
            offices=["Mayor"],
            timezone=None,
            status="verified",
            confidence="official",
            confidence_label="Confirmed official",
            confidence_blurb="",
            source_url="https://elections.example.gov/x",
            source_retrieved_at=None,
            verified_by="editorial",
            verified_at=None,
            notes=None,
            deadlines=[],
            _today=datetime.date(2026, 7, 26),
        )
        base.update(overrides)
        return ElectionView(**base)

    return _factory


@pytest.fixture(scope="session")
def built_site(tmp_path_factory) -> dict[str, str]:
    """Build the real site once and return {relative path: html}."""
    import datetime

    from civic.db import connect as _connect
    from civic.models import ElectionRecord
    from civic.site.build import build_site
    from civic.store import upsert, verify

    out = tmp_path_factory.mktemp("site")
    c = _connect(":memory:")
    recs = [
        ElectionRecord(
            state="TX", jurisdiction_type="state", jurisdiction_name="Texas",
            election_type="general", election_date="2026-11-03",
            offices=["U.S. Senate", "Governor"],
            registration_deadline="2026-10-05", early_voting_start="2026-10-19",
            early_voting_end="2026-10-30", confidence="official",
            source_url="https://sos.example.gov/tx",
        ),
        ElectionRecord(
            state="VA", jurisdiction_type="municipality",
            jurisdiction_name="Town of Example", election_type="municipal",
            election_date="2026-09-08", offices=["Mayor"],
            registration_deadline="2026-08-17", confidence="official",
            source_url="https://elections.example.gov/town",
        ),
    ]
    for r in recs:
        res = upsert(c, r, actor="test")
        verify(c, res.election_id, "test")
    c.commit()
    build_site(
        c, str(out), origin="https://example.test", version="2026.07.26",
        today=datetime.date(2026, 7, 26),
    )
    c.close()
    pages = {}
    for p in out.rglob("*.html"):
        pages[str(p.relative_to(out))] = p.read_text(encoding="utf-8")
    return pages
