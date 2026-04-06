"""
tests/test_autosave.py
Unit tests for autosave.py
"""
import time
import tempfile
import threading
from pathlib import Path

import pytest

# Patch AUTOSAVE_DIR before importing
import autosave


@pytest.fixture(autouse=True)
def tmp_autosave_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(autosave, "AUTOSAVE_DIR", tmp_path)
    monkeypatch.setattr(autosave, "AUTOSAVE_FLAG", tmp_path / ".autosave_active")
    return tmp_path


def test_autosaver_creates_file(tmp_path):
    saved = []
    saver = autosave.AutoSaver(get_transcript=lambda: "hello world", interval=1)
    saver.on_save = saved.append
    saver.start()
    time.sleep(2.2)
    saver.stop()
    assert len(saved) >= 1
    # File was created then cleaned up on clean stop
    # (last autosave deleted on stop)


def test_autosaver_disabled_when_interval_zero():
    saver = autosave.AutoSaver(get_transcript=lambda: "text", interval=0)
    saver.start()
    assert saver._thread is None
    saver.stop()


def test_autosaver_skips_empty_transcript():
    saved = []
    saver = autosave.AutoSaver(get_transcript=lambda: "   ", interval=1)
    saver.on_save = saved.append
    saver.start()
    time.sleep(2.2)
    saver.stop()
    assert len(saved) == 0


def test_crash_flag_written_on_start(tmp_path):
    flag = tmp_path / ".autosave_active"
    import autosave as av
    saver = av.AutoSaver(get_transcript=lambda: "data", interval=60)
    saver.start()
    assert flag.exists()
    saver.stop()
    assert not flag.exists()


def test_check_for_crash_recovery_no_flag(tmp_path):
    result = autosave.check_for_crash_recovery()
    assert result is None


def test_check_for_crash_recovery_with_flag(tmp_path):
    flag = tmp_path / ".autosave_active"
    flag.write_text("2026-04-06T10:00:00")
    save = tmp_path / "autosave_20260406_100000.txt"
    save.write_text("recovered content")
    result = autosave.check_for_crash_recovery()
    assert result == str(save)
    assert not flag.exists()
