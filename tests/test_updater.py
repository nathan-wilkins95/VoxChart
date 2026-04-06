"""
tests/test_updater.py
Unit tests for updater.py
"""
import json
import threading
import time
import unittest
from io import BytesIO
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from updater import _fetch_latest, check_for_update


def _make_response(tag: str, url: str, body: str, status: int = 200):
    """Build a mock urlopen response."""
    payload = json.dumps({"tag_name": tag, "html_url": url, "body": body}).encode()
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read = MagicMock(return_value=payload)
    return mock_resp


class TestFetchLatest(unittest.TestCase):

    @patch("updater.urllib.request.urlopen")
    def test_returns_tag_url_notes(self, mock_open):
        mock_open.return_value = _make_response("v1.9.0", "https://example.com/rel", "Bug fixes")
        result = _fetch_latest()
        self.assertIsNotNone(result)
        self.assertEqual(result["tag"], "1.9.0")   # 'v' stripped
        self.assertEqual(result["url"], "https://example.com/rel")
        self.assertEqual(result["notes"], "Bug fixes")

    @patch("updater.urllib.request.urlopen")
    def test_notes_truncated_at_600_chars(self, mock_open):
        long_notes = "x" * 700
        mock_open.return_value = _make_response("v2.0.0", "https://example.com", long_notes)
        result = _fetch_latest()
        self.assertLessEqual(len(result["notes"]), 600)
        self.assertTrue(result["notes"].endswith("..."))

    @patch("updater.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_returns_none_on_failure(self, _):
        result = _fetch_latest()
        self.assertIsNone(result)

    @patch("updater.urllib.request.urlopen")
    def test_empty_body_becomes_empty_string(self, mock_open):
        payload = json.dumps({"tag_name": "v1.0.0", "html_url": "https://x.com", "body": None}).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read = MagicMock(return_value=payload)
        mock_open.return_value = mock_resp
        result = _fetch_latest()
        self.assertEqual(result["notes"], "")


class TestCheckForUpdate(unittest.TestCase):

    def _run_sync(self, current, latest_tag, url="https://example.com", notes=""):
        """Helper: runs check_for_update and blocks until the bg thread finishes."""
        called_with   = []
        up_to_date    = []
        event         = threading.Event()

        def on_update(ver, u, n):
            called_with.append((ver, u, n))
            event.set()

        def on_utd():
            up_to_date.append(True)
            event.set()

        with patch("updater._fetch_latest",
                   return_value={"tag": latest_tag, "url": url, "notes": notes}):
            check_for_update(current, on_update_available=on_update, on_up_to_date=on_utd)
            event.wait(timeout=3)

        return called_with, up_to_date

    def test_calls_on_update_when_newer(self):
        called, _ = self._run_sync("1.8.0", "1.9.0")
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0][0], "1.9.0")

    def test_calls_on_up_to_date_when_current(self):
        _, utd = self._run_sync("1.9.0", "1.9.0")
        self.assertEqual(utd, [True])

    def test_does_not_call_update_when_already_latest(self):
        called, _ = self._run_sync("2.0.0", "1.9.0")
        self.assertEqual(called, [])

    def test_passes_notes_to_callback(self):
        called, _ = self._run_sync("1.0.0", "2.0.0", notes="Big release!")
        self.assertEqual(called[0][2], "Big release!")

    def test_no_crash_when_fetch_returns_none(self):
        """Should silently do nothing if offline."""
        event = threading.Event()
        with patch("updater._fetch_latest", return_value=None):
            check_for_update("1.0.0", on_update_available=lambda *a: event.set())
            event.wait(timeout=1)
        # No assertion needed — just must not raise


if __name__ == "__main__":
    unittest.main()
