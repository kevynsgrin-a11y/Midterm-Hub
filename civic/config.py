"""Environment-driven settings with sensible defaults.

All configuration is read from the process environment so that the same code runs
in local development, CI, and a production droplet without code changes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str
    export_dir: str
    raw_dir: str
    user_agent: str
    ics_domain: str
    rate_limit_seconds: float


def get_settings() -> Settings:
    """Build a Settings snapshot from the current environment."""
    return Settings(
        db_path=os.environ.get("CIVIC_DB_PATH", "data/civic.db"),
        export_dir=os.environ.get("CIVIC_EXPORT_DIR", "exports/"),
        raw_dir=os.environ.get("CIVIC_RAW_DIR", "data/raw/"),
        user_agent=os.environ.get(
            "CIVIC_USER_AGENT", "CivicCalendarBot/0.1 (+https://example.com/bot)"
        ),
        ics_domain=os.environ.get("CIVIC_ICS_DOMAIN", "civic-calendar.local"),
        rate_limit_seconds=float(os.environ.get("CIVIC_RATE_LIMIT_SECONDS", "2.0")),
    )
