"""State adapter protocol and registry (Phase 2).

Adapters are pure parsers: the CLI orchestrates polite fetching via ``httpclient`` and
passes raw bytes to ``parse``, which keeps every adapter testable from saved fixtures
alone. This module defines the protocol and an empty registry; concrete VA/NJ/TX
adapters arrive in Phase 2.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import ElectionRecord


@runtime_checkable
class StateAdapter(Protocol):
    state: str
    source_urls: list[str]

    def parse(self, html: bytes, source_url: str) -> list[ElectionRecord]:
        ...


# Populated in Phase 2 as adapters are implemented, keyed by module name.
REGISTRY: dict[str, StateAdapter] = {}


def register(adapter: StateAdapter) -> StateAdapter:
    REGISTRY[adapter.state.lower()] = adapter
    return adapter
