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
