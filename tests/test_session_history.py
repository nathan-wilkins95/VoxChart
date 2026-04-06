"""
tests/test_session_history.py
Unit tests for session_history.py
"""
import pytest
from pathlib import Path

import session_history as sh


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_sessions.db"
    monkeypatch.setattr(sh, "DB_PATH", db_path)
    sh.init_db()
    return db_path


def test_init_db_creates_file(tmp_path):
    assert (tmp_path / "test_sessions.db").exists()


def test_start_session_returns_id():
    sid = sh.start_session("chart_notes/test.txt")
    assert isinstance(sid, int)
    assert sid > 0


def test_list_sessions_empty():
    sessions = sh.list_sessions()
    assert sessions == []


def test_list_sessions_after_start():
    sh.start_session("chart_notes/test.txt")
    sessions = sh.list_sessions()
    assert len(sessions) == 1


def test_stop_session_updates_record():
    sid = sh.start_session("chart_notes/test.txt")
    sh.stop_session(sid, "Patient reports chest pain.")
    sessions = sh.list_sessions()
    assert sessions[0]["word_count"] == 4
    assert sessions[0]["duration_sec"] is not None


def test_delete_session():
    sid = sh.start_session("chart_notes/test.txt")
    sh.delete_session(sid)
    assert sh.list_sessions() == []


def test_multiple_sessions_ordered():
    sh.start_session("f1.txt")
    sh.start_session("f2.txt")
    sh.start_session("f3.txt")
    sessions = sh.list_sessions()
    assert len(sessions) == 3
    # Most recent first
    ids = [s["id"] for s in sessions]
    assert ids == sorted(ids, reverse=True)
