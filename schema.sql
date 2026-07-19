PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS elections (
  id TEXT PRIMARY KEY,               -- deterministic, see ids.py
  state TEXT NOT NULL CHECK (length(state) = 2),
  jurisdiction_type TEXT NOT NULL CHECK (jurisdiction_type IN
    ('state','county','municipality','school_district','special_district')),
  jurisdiction_name TEXT NOT NULL,
  jurisdiction_slug TEXT NOT NULL,
  election_date TEXT NOT NULL,       -- ISO 8601 date (YYYY-MM-DD)
  election_type TEXT NOT NULL CHECK (election_type IN
    ('primary','general','runoff','special','municipal','school_board','ballot_measure')),
  offices TEXT NOT NULL DEFAULT '[]',            -- JSON array of strings
  registration_deadline TEXT,                    -- ISO date
  registration_deadline_time TEXT,               -- 'HH:MM' local, optional
  early_voting_start TEXT,                       -- ISO date
  early_voting_end TEXT,                         -- ISO date
  mail_ballot_request_deadline TEXT,             -- ISO date
  candidate_filing_deadline TEXT,                -- ISO date
  timezone TEXT,                                 -- IANA tz string, optional
  status TEXT NOT NULL DEFAULT 'unverified' CHECK (status IN
    ('unverified','verified','needs_review','superseded','cancelled')),
  confidence TEXT NOT NULL DEFAULT 'secondary' CHECK (confidence IN
    ('official','secondary','inferred')),
  source_url TEXT NOT NULL,
  source_retrieved_at TEXT NOT NULL,             -- ISO 8601 datetime UTC
  verified_by TEXT,
  verified_at TEXT,
  notes TEXT,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_elections_state_date ON elections(state, election_date);
CREATE INDEX IF NOT EXISTS idx_elections_status ON elections(status);

CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  election_id TEXT NOT NULL REFERENCES elections(id),
  field TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  detected_at TEXT NOT NULL,          -- ISO 8601 datetime UTC
  source_url TEXT,
  applied INTEGER NOT NULL DEFAULT 0  -- 0 = pending review, 1 = applied, 2 = rejected
);
CREATE INDEX IF NOT EXISTS idx_changes_election ON changes(election_id);
CREATE INDEX IF NOT EXISTS idx_changes_applied ON changes(applied);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  state TEXT NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  adapter TEXT,                        -- adapter module name; NULL = manual-only reference
  check_frequency_days INTEGER NOT NULL DEFAULT 14,
  last_checked_at TEXT,
  last_changed_at TEXT,
  enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS export_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version TEXT NOT NULL,               -- e.g. '2026.07.19'
  kind TEXT NOT NULL CHECK (kind IN ('json','csv','ics')),
  record_count INTEGER NOT NULL,
  file_manifest TEXT NOT NULL,         -- JSON: [{"path": ..., "sha256": ...}]
  created_at TEXT NOT NULL
);
