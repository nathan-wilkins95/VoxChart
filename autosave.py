"""
autosave.py
Periodic auto-save of the live transcript during a recording session.
Also handles crash-recovery by detecting a leftover autosave on startup.
"""
from __future__ import annotations
import threading
import logging
import time
from datetime import datetime
from pathlib import Path

AUTOSAVE_DIR  = Path("chart_notes")
AUTOSAVE_FLAG = Path("chart_notes/.autosave_active")
logger = logging.getLogger("voxchart.autosave")


class AutoSaver:
    """
    Usage:
        saver = AutoSaver(get_transcript_fn, interval=60)
        saver.start()          # call when recording begins
        saver.stop()           # call when recording stops cleanly
        saver.on_save = fn     # optional callback(path) after each save
    """
    def __init__(self, get_transcript, interval: int = 60):
        self._get    = get_transcript  # callable -> str
        self.interval = interval        # seconds between saves; 0 = disabled
        self._stop   = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_save = None             # optional callback(save_path: str)
        self._last_path: str | None = None

    def start(self):
        if self.interval <= 0:
            return
        AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
        AUTOSAVE_FLAG.write_text(datetime.now().isoformat(), encoding="utf-8")
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="voxchart-autosave")
        self._thread.start()
        logger.info("AutoSaver started (interval=%ds)", self.interval)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        # Clean up the crash-detection flag on a normal stop
        try:
            AUTOSAVE_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        # Remove the latest autosave file on clean stop (note is saved by user)
        if self._last_path:
            try:
                Path(self._last_path).unlink(missing_ok=True)
            except Exception:
                pass
        logger.info("AutoSaver stopped")

    def _loop(self):
        time.sleep(self.interval)
        while not self._stop.is_set():
            self._save()
            time.sleep(self.interval)

    def _save(self):
        try:
            text = self._get()
            if not text.strip():
                return
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = AUTOSAVE_DIR / f"autosave_{ts}.txt"
            path.write_text(text, encoding="utf-8")
            # Remove previous autosave
            if self._last_path and self._last_path != str(path):
                try:
                    Path(self._last_path).unlink(missing_ok=True)
                except Exception:
                    pass
            self._last_path = str(path)
            logger.info("Auto-saved to %s", path)
            if self.on_save:
                self.on_save(str(path))
        except Exception as e:
            logger.warning("Auto-save failed: %s", e)


def check_for_crash_recovery() -> str | None:
    """
    Call on startup. Returns the path to the most recent autosave file
    if the app crashed during a recording, otherwise None.
    """
    if not AUTOSAVE_FLAG.exists():
        return None
    # Flag exists → app didn't stop cleanly
    saves = sorted(AUTOSAVE_DIR.glob("autosave_*.txt"), reverse=True)
    AUTOSAVE_FLAG.unlink(missing_ok=True)
    return str(saves[0]) if saves else None
