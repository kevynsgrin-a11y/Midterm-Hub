"""civic-calendar-engine: a curation-first U.S. off-cycle election calendar pipeline.

Phase 1 provides deterministic identity, a Pydantic validation layer, SQLite-backed
storage with audited upsert semantics, manual YAML intake, and JSON/CSV/ICS exports.
The system is fully useful with zero scrapers; adapters (Phase 2) only assist curation.
"""

__version__ = "0.1.0"
