import sqlite3
import json
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mneme_audit.db")


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
            response_text TEXT NOT NULL
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
            resolution_notes TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("[Audit] Database initialized")


def log_interaction(session_id: str, role: str, query: str, query_redacted: str, response: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO audit_log
           (timestamp, session_id, role, query, query_redacted, outcome, confidence, routing_target, sources_json, response_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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


def create_ticket(session_id: str, initiator_role: str, target_team: str,
                  priority: str, summary: str, escalation_reason: str = "") -> str:
    ticket_id = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO escalation_tickets
           (ticket_id, timestamp, session_id, initiator_role, target_team, priority, summary, escalation_reason, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')""",
        (ticket_id, datetime.utcnow().isoformat(), session_id, initiator_role,
         target_team, priority, summary, escalation_reason),
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


def resolve_ticket(ticket_id: str, notes: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "UPDATE escalation_tickets SET status='RESOLVED', resolution_notes=? WHERE ticket_id=?",
        (notes, ticket_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0
