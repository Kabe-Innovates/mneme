import sqlite3
import json
import os
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
