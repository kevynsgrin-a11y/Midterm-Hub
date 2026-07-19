"""Upsert semantics, review workflow, and change-log queries — the accuracy core.

The single most important invariant: **verified data is never silently overwritten.**
A conflicting re-ingest of a verified record queues field-level changes for human
review and flips the record to ``needs_review`` without touching stored values.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Optional

from .ids import SUBSTANTIVE_FIELDS, content_hash, election_id
from .models import ElectionRecord


@dataclass
class UpsertResult:
    action: str  # 'inserted' | 'touched' | 'queued_review' | 'updated'
    election_id: str
    change_ids: list[int] = field(default_factory=list)


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dt_to_iso_z(dt: datetime.datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_str(v: Optional[datetime.date]) -> Optional[str]:
    return v.isoformat() if isinstance(v, datetime.date) else v


def _record_columns(record: ElectionRecord) -> dict[str, Any]:
    """Map an ElectionRecord to its serialized election-table column values (excluding
    id, status, verification, hash and timestamp bookkeeping)."""
    return {
        "state": record.state,
        "jurisdiction_type": record.jurisdiction_type,
        "jurisdiction_name": record.jurisdiction_name,
        "jurisdiction_slug": record.jurisdiction_slug,
        "election_date": record.election_date.isoformat(),
        "election_type": record.election_type,
        "offices": json.dumps(record.offices),
        "registration_deadline": _date_str(record.registration_deadline),
        "registration_deadline_time": record.registration_deadline_time,
        "early_voting_start": _date_str(record.early_voting_start),
        "early_voting_end": _date_str(record.early_voting_end),
        "mail_ballot_request_deadline": _date_str(record.mail_ballot_request_deadline),
        "candidate_filing_deadline": _date_str(record.candidate_filing_deadline),
        "timezone": record.timezone,
        "confidence": record.confidence,
        "source_url": record.source_url,
        "notes": record.notes,
    }


def _row_substantive_view(row: sqlite3.Row) -> dict[str, Any]:
    """Build the hashable substantive view from a DB row (offices back to a list)."""
    view = {k: row[k] for k in SUBSTANTIVE_FIELDS}
    view["offices"] = json.loads(row["offices"]) if row["offices"] else []
    return view


def _substantive_diff(row: sqlite3.Row, cols: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    """Field-level diff over substantive fields, comparing stored serialized values to
    the incoming serialized column values."""
    diffs: list[tuple[str, Any, Any]] = []
    for f in SUBSTANTIVE_FIELDS:
        old_v = row[f]
        new_v = cols[f]
        if old_v != new_v:
            diffs.append((f, old_v, new_v))
    return diffs


def _recompute_hash(conn: sqlite3.Connection, eid: str) -> str:
    row = conn.execute("SELECT * FROM elections WHERE id = ?", (eid,)).fetchone()
    new_hash = content_hash(_row_substantive_view(row))
    conn.execute("UPDATE elections SET content_hash = ? WHERE id = ?", (new_hash, eid))
    return new_hash


def upsert(conn: sqlite3.Connection, record: ElectionRecord, actor: str) -> UpsertResult:
    """Idempotently ingest a record following the four-path accuracy protocol."""
    now = _utcnow_iso()
    retrieved = _dt_to_iso_z(record.source_retrieved_at)
    eid = election_id(
        record.state, record.jurisdiction_slug, record.election_date.isoformat(), record.election_type
    )
    chash = content_hash(record)
    cols = _record_columns(record)

    existing = conn.execute("SELECT * FROM elections WHERE id = ?", (eid,)).fetchone()

    # Path 1: brand-new election.
    if existing is None:
        conn.execute(
            """
            INSERT INTO elections (
                id, state, jurisdiction_type, jurisdiction_name, jurisdiction_slug,
                election_date, election_type, offices, registration_deadline,
                registration_deadline_time, early_voting_start, early_voting_end,
                mail_ballot_request_deadline, candidate_filing_deadline, timezone,
                status, confidence, source_url, source_retrieved_at,
                verified_by, verified_at, notes, content_hash, created_at, updated_at
            ) VALUES (
                :id, :state, :jurisdiction_type, :jurisdiction_name, :jurisdiction_slug,
                :election_date, :election_type, :offices, :registration_deadline,
                :registration_deadline_time, :early_voting_start, :early_voting_end,
                :mail_ballot_request_deadline, :candidate_filing_deadline, :timezone,
                'unverified', :confidence, :source_url, :source_retrieved_at,
                NULL, NULL, :notes, :content_hash, :created_at, :updated_at
            )
            """,
            {
                **cols,
                "id": eid,
                "source_retrieved_at": retrieved,
                "content_hash": chash,
                "created_at": now,
                "updated_at": now,
            },
        )
        return UpsertResult(action="inserted", election_id=eid)

    # Path 2: identical substance — refresh provenance only.
    if existing["content_hash"] == chash:
        conn.execute(
            "UPDATE elections SET source_retrieved_at = ?, updated_at = ? WHERE id = ?",
            (retrieved, now, eid),
        )
        return UpsertResult(action="touched", election_id=eid)

    # Substance differs: compute the field-level diff.
    diffs = _substantive_diff(existing, cols)

    # Path 3: protect verified data — queue changes for review, mutate nothing.
    if existing["status"] == "verified":
        change_ids: list[int] = []
        for f, old_v, new_v in diffs:
            cur = conn.execute(
                """
                INSERT INTO changes (election_id, field, old_value, new_value,
                                     detected_at, source_url, applied)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (eid, f, old_v, new_v, now, record.source_url),
            )
            change_ids.append(int(cur.lastrowid))
        conn.execute(
            "UPDATE elections SET status = 'needs_review', source_retrieved_at = ?, "
            "updated_at = ? WHERE id = ?",
            (retrieved, now, eid),
        )
        return UpsertResult(action="queued_review", election_id=eid, change_ids=change_ids)

    # Path 4: unverified (or otherwise unprotected) — apply new values, log as applied.
    change_ids = []
    for f, old_v, new_v in diffs:
        cur = conn.execute(
            """
            INSERT INTO changes (election_id, field, old_value, new_value,
                                 detected_at, source_url, applied)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (eid, f, old_v, new_v, now, record.source_url),
        )
        change_ids.append(int(cur.lastrowid))
    conn.execute(
        """
        UPDATE elections SET
            jurisdiction_name = :jurisdiction_name,
            jurisdiction_slug = :jurisdiction_slug,
            offices = :offices,
            registration_deadline = :registration_deadline,
            registration_deadline_time = :registration_deadline_time,
            early_voting_start = :early_voting_start,
            early_voting_end = :early_voting_end,
            mail_ballot_request_deadline = :mail_ballot_request_deadline,
            candidate_filing_deadline = :candidate_filing_deadline,
            timezone = :timezone,
            confidence = :confidence,
            source_url = :source_url,
            source_retrieved_at = :source_retrieved_at,
            notes = :notes,
            content_hash = :content_hash,
            updated_at = :updated_at
        WHERE id = :id
        """,
        {
            **cols,
            "id": eid,
            "source_retrieved_at": retrieved,
            "content_hash": chash,
            "updated_at": now,
        },
    )
    return UpsertResult(action="updated", election_id=eid, change_ids=change_ids)


def verify(conn: sqlite3.Connection, election_id_value: str, actor: str) -> bool:
    """Mark an election verified. Returns False if the election does not exist."""
    now = _utcnow_iso()
    cur = conn.execute(
        "UPDATE elections SET status = 'verified', verified_by = ?, verified_at = ?, "
        "updated_at = ? WHERE id = ?",
        (actor, now, now, election_id_value),
    )
    return cur.rowcount > 0


def _restore_verified_if_settled(conn: sqlite3.Connection, eid: str) -> None:
    """If no pending changes remain for an election, restore it to verified."""
    remaining = conn.execute(
        "SELECT COUNT(*) FROM changes WHERE election_id = ? AND applied = 0", (eid,)
    ).fetchone()[0]
    if remaining == 0:
        conn.execute(
            "UPDATE elections SET status = 'verified', updated_at = ? WHERE id = ?",
            (_utcnow_iso(), eid),
        )


def approve_change(conn: sqlite3.Connection, change_id: int, actor: str) -> None:
    """Apply a pending change's new value, recompute the hash, and settle status."""
    row = conn.execute("SELECT * FROM changes WHERE id = ?", (change_id,)).fetchone()
    if row is None:
        raise ValueError(f"no such change: {change_id}")
    if row["applied"] != 0:
        raise ValueError(f"change {change_id} is not pending (applied={row['applied']})")

    field_name = row["field"]
    if field_name not in SUBSTANTIVE_FIELDS:
        raise ValueError(f"refusing to apply change to non-substantive field {field_name!r}")

    eid = row["election_id"]
    conn.execute(
        f"UPDATE elections SET {field_name} = ?, updated_at = ? WHERE id = ?",
        (row["new_value"], _utcnow_iso(), eid),
    )
    conn.execute("UPDATE changes SET applied = 1 WHERE id = ?", (change_id,))
    _recompute_hash(conn, eid)
    _restore_verified_if_settled(conn, eid)


def reject_change(conn: sqlite3.Connection, change_id: int, actor: str) -> None:
    """Discard a pending change and settle status; stored values are untouched."""
    row = conn.execute("SELECT * FROM changes WHERE id = ?", (change_id,)).fetchone()
    if row is None:
        raise ValueError(f"no such change: {change_id}")
    if row["applied"] != 0:
        raise ValueError(f"change {change_id} is not pending (applied={row['applied']})")

    conn.execute("UPDATE changes SET applied = 2 WHERE id = ?", (change_id,))
    _restore_verified_if_settled(conn, row["election_id"])


def pending_reviews(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Elections in needs_review with their pending (applied=0) changes."""
    elections = conn.execute(
        "SELECT * FROM elections WHERE status = 'needs_review' ORDER BY state, election_date"
    ).fetchall()
    result: list[dict[str, Any]] = []
    for e in elections:
        changes = conn.execute(
            "SELECT * FROM changes WHERE election_id = ? AND applied = 0 ORDER BY id",
            (e["id"],),
        ).fetchall()
        result.append({"election": dict(e), "changes": [dict(c) for c in changes]})
    return result


def diff_since(conn: sqlite3.Connection, since_iso_date: str) -> list[dict[str, Any]]:
    """Applied changes plus newly-inserted elections since a date, grouped by election.

    ``since_iso_date`` is compared lexically against ISO timestamps, so a plain date
    like ``2026-07-01`` correctly includes everything from that day onward.
    """
    grouped: dict[str, dict[str, Any]] = {}

    new_rows = conn.execute(
        "SELECT * FROM elections WHERE created_at >= ? ORDER BY state, election_date",
        (since_iso_date,),
    ).fetchall()
    for e in new_rows:
        grouped[e["id"]] = {"election": dict(e), "is_new": True, "changes": []}

    change_rows = conn.execute(
        "SELECT * FROM changes WHERE applied = 1 AND detected_at >= ? "
        "ORDER BY election_id, id",
        (since_iso_date,),
    ).fetchall()
    for c in change_rows:
        eid = c["election_id"]
        if eid not in grouped:
            e = conn.execute("SELECT * FROM elections WHERE id = ?", (eid,)).fetchone()
            grouped[eid] = {"election": dict(e), "is_new": False, "changes": []}
        grouped[eid]["changes"].append(dict(c))

    # Stable ordering for deterministic changelogs.
    return sorted(
        grouped.values(),
        key=lambda g: (g["election"]["state"], g["election"]["election_date"], g["election"]["id"]),
    )
