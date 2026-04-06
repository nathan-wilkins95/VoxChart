"""
session_history.py
Persists dictation session metadata to sessions.db (SQLite).
Each session: id, started_at, stopped_at, duration_sec, word_count, file_path.
"""
from __future__ import annotations
import csv
import io
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

DB_PATH = Path("sessions.db")
logger  = logging.getLogger("voxchart.history")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at   TEXT NOT NULL,
                stopped_at   TEXT,
                duration_sec REAL,
                word_count   INTEGER,
                file_path    TEXT
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
    stopped    = datetime.now().isoformat()
    word_count = len(transcript.split())
    with _connect() as conn:
        row = conn.execute(
            "SELECT started_at FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        duration = 0.0
        if row:
            try:
                t0       = datetime.fromisoformat(row["started_at"])
                t1       = datetime.fromisoformat(stopped)
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


def search_sessions(query: str, limit: int = 100) -> list[dict]:
    """
    Search sessions by transcript content or file path.
    Returns sessions whose file_path contains the query OR whose
    transcript file content contains the query (case-insensitive).
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return list_sessions(limit)

    all_sessions = list_sessions(limit=1000)
    results = []
    for s in all_sessions:
        # Match on file path
        if query_lower in (s.get("file_path") or "").lower():
            results.append(s)
            continue
        # Match on transcript content
        text = read_transcript(s.get("file_path", "")).lower()
        if query_lower in text:
            results.append(s)
        if len(results) >= limit:
            break
    return results


def export_sessions_csv(session_ids: list[int] | None = None) -> str:
    """
    Export session metadata (and transcript snippets) to a CSV string.
    If session_ids is None, exports all sessions.
    Returns the CSV as a string (caller writes to file or clipboard).
    """
    init_db()
    with _connect() as conn:
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            rows = conn.execute(
                f"SELECT * FROM sessions WHERE id IN ({placeholders}) ORDER BY id DESC",
                session_ids
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC"
            ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "started_at", "stopped_at", "duration_sec",
                     "word_count", "file_path", "transcript_preview"])
    for row in rows:
        d = dict(row)
        preview = read_transcript(d.get("file_path", ""))[:200].replace("\n", " ")
        writer.writerow([
            d["id"], d["started_at"], d["stopped_at"],
            d["duration_sec"], d["word_count"], d["file_path"], preview
        ])
    return output.getvalue()
