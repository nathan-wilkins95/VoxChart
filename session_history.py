"""
session_history.py
Persists dictation session metadata to sessions.db (SQLite).
Each session: id, started_at, stopped_at, duration_sec, word_count, file_path.
"""
from __future__ import annotations
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

DB_PATH = Path("sessions.db")
logger = logging.getLogger("voxchart.history")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at  TEXT NOT NULL,
                stopped_at  TEXT,
                duration_sec REAL,
                word_count  INTEGER,
                file_path   TEXT
            )
        """)
        conn.commit()


def start_session(file_path: str) -> int:
    """Insert a new session row and return its id."""
    init_db()
    started = datetime.now().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (started_at, file_path) VALUES (?, ?)",
            (started, file_path)
        )
        conn.commit()
        return cur.lastrowid


def stop_session(session_id: int, transcript: str):
    """Update session row with stop time, duration, and word count."""
    stopped = datetime.now().isoformat()
    word_count = len(transcript.split())
    with _connect() as conn:
        # calculate duration
        row = conn.execute("SELECT started_at FROM sessions WHERE id=?", (session_id,)).fetchone()
        duration = 0.0
        if row:
            try:
                t0 = datetime.fromisoformat(row["started_at"])
                t1 = datetime.fromisoformat(stopped)
                duration = (t1 - t0).total_seconds()
            except Exception:
                pass
        conn.execute(
            "UPDATE sessions SET stopped_at=?, duration_sec=?, word_count=? WHERE id=?",
            (stopped, duration, word_count, session_id)
        )
        conn.commit()
    logger.info("Session %d saved: %.0fs, %d words", session_id, duration, word_count)


def list_sessions(limit: int = 100) -> list[dict]:
    """Return recent sessions newest-first."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()
    logger.info("Session %d deleted", session_id)


def read_transcript(file_path: str) -> str:
    """Read a saved transcript file, return empty string if missing."""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except Exception:
        return ""
