"""Upsert semantics and the review cycle — the most important tests in the repo.

Covers all four upsert paths (inserted / touched / queued_review / updated) and the
end-to-end protection guarantee: a conflicting re-ingest of a VERIFIED record queues
changes, does NOT mutate stored values, and approve/reject correctly settle status.
"""
from __future__ import annotations

import pytest

from civic.store import (
    approve_change,
    diff_since,
    pending_reviews,
    reject_change,
    upsert,
    verify,
)


def _row(conn, eid):
    return conn.execute("SELECT * FROM elections WHERE id = ?", (eid,)).fetchone()


def _pending(conn, eid):
    return conn.execute(
        "SELECT * FROM changes WHERE election_id = ? AND applied = 0 ORDER BY id", (eid,)
    ).fetchall()


class TestUpsertPaths:
    def test_inserted(self, conn, make_record):
        res = upsert(conn, make_record(), actor="tester")
        assert res.action == "inserted"
        row = _row(conn, res.election_id)
        assert row["status"] == "unverified"
        assert row["created_at"] and row["updated_at"]
        assert row["content_hash"]

    def test_touched_when_identical(self, conn, make_record):
        r1 = upsert(conn, make_record(), actor="tester")
        before = _row(conn, r1.election_id)
        r2 = upsert(conn, make_record(), actor="tester")
        assert r2.action == "touched"
        after = _row(conn, r1.election_id)
        # No changes rows, content unchanged.
        assert conn.execute("SELECT COUNT(*) FROM changes").fetchone()[0] == 0
        assert after["content_hash"] == before["content_hash"]
        assert after["registration_deadline"] == before["registration_deadline"]

    def test_updated_when_unverified_and_changed(self, conn, make_record):
        r1 = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="tester")
        r2 = upsert(conn, make_record(registration_deadline="2027-04-15"), actor="tester")
        assert r2.action == "updated"
        row = _row(conn, r1.election_id)
        assert row["registration_deadline"] == "2027-04-15"  # value applied
        # Exactly one applied change logged for the differing field.
        changes = conn.execute("SELECT * FROM changes WHERE applied = 1").fetchall()
        assert len(changes) == 1
        assert changes[0]["field"] == "registration_deadline"
        assert changes[0]["old_value"] == "2027-04-12"
        assert changes[0]["new_value"] == "2027-04-15"

    def test_queued_review_when_verified_and_changed(self, conn, make_record):
        r1 = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="tester")
        verify(conn, r1.election_id, "curator")
        r2 = upsert(conn, make_record(registration_deadline="2027-04-15"), actor="tester")
        assert r2.action == "queued_review"
        row = _row(conn, r1.election_id)
        assert row["status"] == "needs_review"
        # Value must NOT have changed.
        assert row["registration_deadline"] == "2027-04-12"
        pend = _pending(conn, r1.election_id)
        assert len(pend) == 1
        assert pend[0]["applied"] == 0
        assert set(r2.change_ids) == {pend[0]["id"]}


class TestReviewCycleApprove:
    def test_verify_then_conflict_then_approve_restores_verified(self, conn, make_record):
        # Insert + verify.
        r1 = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="t")
        eid = r1.election_id
        verify(conn, eid, "curator")
        assert _row(conn, eid)["status"] == "verified"
        verified_hash = _row(conn, eid)["content_hash"]

        # Conflicting re-ingest queues review and protects the value.
        upsert(conn, make_record(registration_deadline="2027-04-15"), actor="t")
        assert _row(conn, eid)["status"] == "needs_review"
        assert _row(conn, eid)["registration_deadline"] == "2027-04-12"
        assert _row(conn, eid)["content_hash"] == verified_hash  # hash unchanged too

        # It appears in review.
        reviews = pending_reviews(conn)
        assert len(reviews) == 1
        assert reviews[0]["election"]["id"] == eid
        change_id = reviews[0]["changes"][0]["id"]

        # Approve applies the value, recomputes the hash, restores verified.
        approve_change(conn, change_id, "curator")
        row = _row(conn, eid)
        assert row["registration_deadline"] == "2027-04-15"
        assert row["status"] == "verified"
        assert row["content_hash"] != verified_hash
        assert _pending(conn, eid) == []
        assert conn.execute(
            "SELECT applied FROM changes WHERE id = ?", (change_id,)
        ).fetchone()[0] == 1


class TestReviewCycleReject:
    def test_reject_discards_and_restores_verified(self, conn, make_record):
        r1 = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="t")
        eid = r1.election_id
        verify(conn, eid, "curator")
        verified_hash = _row(conn, eid)["content_hash"]

        upsert(conn, make_record(registration_deadline="2027-04-15"), actor="t")
        change_id = _pending(conn, eid)[0]["id"]

        reject_change(conn, change_id, "curator")
        row = _row(conn, eid)
        assert row["registration_deadline"] == "2027-04-12"  # unchanged
        assert row["content_hash"] == verified_hash
        assert row["status"] == "verified"
        assert _pending(conn, eid) == []
        assert conn.execute(
            "SELECT applied FROM changes WHERE id = ?", (change_id,)
        ).fetchone()[0] == 2


class TestProtectionAcrossSecondConflict:
    """Regression for the critical bug: a verified record already in needs_review must
    keep queuing further conflicts — never silently apply an unreviewed value."""

    def test_second_conflict_still_queues_and_protects(self, conn, make_record):
        r1 = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="t")
        eid = r1.election_id
        verify(conn, eid, "curator")
        verified_hash = _row(conn, eid)["content_hash"]

        upsert(conn, make_record(registration_deadline="2027-04-15"), actor="t")
        assert _row(conn, eid)["status"] == "needs_review"

        # Second conflicting ingest while in needs_review.
        res = upsert(conn, make_record(registration_deadline="2027-04-20"), actor="t")
        assert res.action == "queued_review"  # queued, NOT "updated"
        row = _row(conn, eid)
        assert row["registration_deadline"] == "2027-04-12"  # original, untouched
        assert row["content_hash"] == verified_hash

        # Rejecting one pending change must not restore verified with the bot value.
        pend = _pending(conn, eid)
        assert len(pend) == 2
        reject_change(conn, pend[0]["id"], "curator")
        assert _row(conn, eid)["status"] == "needs_review"
        assert _row(conn, eid)["registration_deadline"] == "2027-04-12"

    def test_verify_refuses_with_pending_changes(self, conn, make_record):
        r = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="t")
        verify(conn, r.election_id, "c")
        upsert(conn, make_record(registration_deadline="2027-04-15"), actor="t")
        with pytest.raises(ValueError):
            verify(conn, r.election_id, "c")


class TestMultiFieldReview:
    def test_partial_approval_keeps_needs_review(self, conn, make_record):
        r1 = upsert(
            conn,
            make_record(registration_deadline="2027-04-12", offices=["Mayor"]),
            actor="t",
        )
        eid = r1.election_id
        verify(conn, eid, "curator")

        # Two differing substantive fields → two pending changes.
        res = upsert(
            conn,
            make_record(registration_deadline="2027-04-15", offices=["Mayor", "Clerk"]),
            actor="t",
        )
        assert res.action == "queued_review"
        pend = _pending(conn, eid)
        assert len(pend) == 2

        # Approve one: still needs_review because one remains.
        approve_change(conn, pend[0]["id"], "curator")
        assert _row(conn, eid)["status"] == "needs_review"

        # Approve the second: settles back to verified.
        approve_change(conn, pend[1]["id"], "curator")
        assert _row(conn, eid)["status"] == "verified"


class TestDiffSince:
    def test_new_and_changed_grouped(self, conn, make_record):
        r1 = upsert(conn, make_record(registration_deadline="2027-04-12"), actor="t")
        # Update (unverified path) produces an applied change.
        upsert(conn, make_record(registration_deadline="2027-04-20"), actor="t")

        groups = diff_since(conn, "1970-01-01")
        assert len(groups) == 1
        g = groups[0]
        assert g["election"]["id"] == r1.election_id
        assert g["is_new"] is True
        # The applied change is captured for the changelog.
        assert any(c["field"] == "registration_deadline" for c in g["changes"])
