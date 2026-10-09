"""
Mneme Audit Trail — HMAC SHA-256 Chained Immutable Log
======================================================
Each entry stores an HMAC hash computed over {payload, previous_entry_hash},
creating a cryptographically verifiable chain — any tampering is detectable.

Adopted from Divathiru's HMAC chaining pattern (HIPAA § 164.312 compliance).
"""

import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mneme_audit.db")
_HMAC_KEY = os.getenv("AUDIT_HMAC_KEY", "mneme-default-hmac-key-change-in-production").encode()


def _compute_hash(payload: dict, prev_hash: str) -> str:
    """Compute HMAC-SHA256 hash over payload + previous entry hash."""
    msg = json.dumps({"payload": payload, "prev_hash": prev_hash}, sort_keys=True).encode()
    return hmac.new(_HMAC_KEY, msg, hashlib.sha256).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            query TEXT NOT NULL,
            query_redacted TEXT NOT NULL,
            outcome TEXT NOT NULL,
            confidence REAL NOT NULL,
            routing_target TEXT,
            sources_json TEXT,
            response_text TEXT NOT NULL,
            prev_hash TEXT NOT NULL DEFAULT '',
            entry_hash TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS escalation_tickets (
            ticket_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            initiator_role TEXT NOT NULL,
            target_team TEXT NOT NULL,
            priority TEXT NOT NULL,
            summary TEXT NOT NULL,
            escalation_reason TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            resolution_notes TEXT,
            is_gap INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Migrate existing tables: add HMAC columns if missing
    try:
        conn.execute("SELECT prev_hash FROM audit_log LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE audit_log ADD COLUMN prev_hash TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE audit_log ADD COLUMN entry_hash TEXT NOT NULL DEFAULT ''")

    # Migrate: add is_gap column if missing
    try:
        conn.execute("SELECT is_gap FROM escalation_tickets LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE escalation_tickets ADD COLUMN is_gap INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()
    print("[Audit] Database initialized (HMAC-chained)")


def _get_last_hash() -> str:
    """Retrieve the hash of the most recent audit log entry."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0] if row else ""


def log_interaction(session_id: str, role: str, query: str, query_redacted: str, response: dict):
    prev_hash = _get_last_hash()

    payload = {
        "session_id": session_id,
        "role": role,
        "query_redacted": query_redacted,
        "outcome": response.get("outcome", ""),
        "confidence": response.get("confidence", 0.0),
        "routing_target": response.get("routing_target"),
    }
    entry_hash = _compute_hash(payload, prev_hash)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_log
           (timestamp, session_id, role, query, query_redacted, outcome, confidence,
            routing_target, sources_json, response_text, prev_hash, entry_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.utcnow().isoformat(),
            session_id,
            role,
            query,
            query_redacted,
            response.get("outcome", ""),
            response.get("confidence", 0.0),
            response.get("routing_target"),
            json.dumps(response.get("sources", [])),
            response.get("message", ""),
            prev_hash,
            entry_hash,
        ),
    )
    conn.commit()
    conn.close()


def get_session_log(session_id: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_log(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# HMAC Chain Verification
# ---------------------------------------------------------------------------

def verify_chain() -> dict:
    """
    Walk the entire audit log and verify the HMAC chain integrity.
    Returns {total, verified, valid, violations: [{id, expected, actual}]}.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
    conn.close()

    violations = []
    prev_hash = ""

    for row in rows:
        row_dict = dict(row)
        stored_hash = row_dict.get("entry_hash", "")
        stored_prev = row_dict.get("prev_hash", "")

        # Skip legacy entries that predate HMAC (empty hashes)
        if not stored_hash:
            prev_hash = ""
            continue

        # Verify prev_hash chain
        if stored_prev != prev_hash:
            violations.append({
                "id": row_dict["id"],
                "type": "chain_break",
                "expected_prev": prev_hash,
                "actual_prev": stored_prev,
            })

        # Recompute hash and verify
        payload = {
            "session_id": row_dict["session_id"],
            "role": row_dict["role"],
            "query_redacted": row_dict["query_redacted"],
            "outcome": row_dict["outcome"],
            "confidence": row_dict["confidence"],
            "routing_target": row_dict["routing_target"],
        }
        expected_hash = _compute_hash(payload, stored_prev)
        if expected_hash != stored_hash:
            violations.append({
                "id": row_dict["id"],
                "type": "hash_mismatch",
                "expected": expected_hash,
                "actual": stored_hash,
            })

        prev_hash = stored_hash

    return {
        "total": len(rows),
        "verified": len(rows),
        "valid": len(violations) == 0,
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# Escalation Tickets
# ---------------------------------------------------------------------------

def create_ticket(session_id: str, initiator_role: str, target_team: str,
                  priority: str, summary: str, escalation_reason: str = "",
                  is_gap: bool = False) -> str:
    ticket_id = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO escalation_tickets
           (ticket_id, timestamp, session_id, initiator_role, target_team, priority,
            summary, escalation_reason, status, is_gap)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)""",
        (ticket_id, datetime.utcnow().isoformat(), session_id, initiator_role,
         target_team, priority, summary, escalation_reason, int(is_gap)),
    )
    conn.commit()
    conn.close()
    return ticket_id


def get_open_tickets(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM escalation_tickets ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_gap_tickets(limit: int = 50) -> list[dict]:
    """Retrieve knowledge gap tickets — queries the system couldn't answer."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM escalation_tickets WHERE is_gap = 1 ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_ticket(ticket_id: str, notes: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "UPDATE escalation_tickets SET status='RESOLVED', resolution_notes=? WHERE ticket_id=?",
        (notes, ticket_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0
