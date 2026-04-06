"""
tests/test_medical_postprocessor.py
Unit tests for medical_postprocessor.py
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMedicalPostprocessor(unittest.TestCase):

    def setUp(self):
        """Each test gets a fresh import with a temp DB path."""
        # Force fresh module state by clearing lru_cache before each test
        import medical_postprocessor as mp
        mp._load_terms.cache_clear()
        self.mp = mp

    def _make_db(self, rows: list[tuple[str, str | None]]) -> Path:
        """Create a temp SQLite DB with given (term, common_misrecognition) rows."""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE terms "
            "(id INTEGER PRIMARY KEY, term TEXT, category TEXT, common_misrecognition TEXT)"
        )
        conn.executemany(
            "INSERT INTO terms (term, common_misrecognition) VALUES (?, ?)", rows
        )
        conn.commit()
        conn.close()
        return db_path

    # ------------------------------------------------------------------
    # Passthrough when DB is missing
    # ------------------------------------------------------------------

    def test_passthrough_when_no_db(self):
        with patch.object(self.mp, "DB_PATH", Path("/nonexistent/medical_terms.db")):
            self.mp._load_terms.cache_clear()
            result = self.mp.correct_medical_text("met four min twice daily")
        self.assertEqual(result, "met four min twice daily")

    def test_empty_string_passthrough(self):
        result = self.mp.correct_medical_text("")
        self.assertEqual(result, "")

    def test_whitespace_only_passthrough(self):
        result = self.mp.correct_medical_text("   ")
        self.assertEqual(result, "   ")

    # ------------------------------------------------------------------
    # Correction applied
    # ------------------------------------------------------------------

    def test_basic_correction(self):
        db = self._make_db([("metformin", "met four min")])
        with patch.object(self.mp, "DB_PATH", db):
            self.mp._load_terms.cache_clear()
            result = self.mp.correct_medical_text("give met four min twice daily")
        self.assertIn("metformin", result)
        db.unlink()

    def test_case_insensitive_correction(self):
        db = self._make_db([("metformin", "met four min")])
        with patch.object(self.mp, "DB_PATH", db):
            self.mp._load_terms.cache_clear()
            result = self.mp.correct_medical_text("give MET FOUR MIN twice daily")
        self.assertIn("metformin", result)
        db.unlink()

    # ------------------------------------------------------------------
    # Whole-word only
    # ------------------------------------------------------------------

    def test_no_partial_word_replacement(self):
        """'mis' should not match inside 'mission'."""
        db = self._make_db([("myocardial", "mis")])
        with patch.object(self.mp, "DB_PATH", db):
            self.mp._load_terms.cache_clear()
            result = self.mp.correct_medical_text("the mission was successful")
        self.assertNotIn("myocardial", result)
        self.assertIn("mission", result)
        db.unlink()

    def test_whole_word_match_at_boundary(self):
        db = self._make_db([("lisinopril", "liz no pril")])
        with patch.object(self.mp, "DB_PATH", db):
            self.mp._load_terms.cache_clear()
            result = self.mp.correct_medical_text("start liz no pril 10mg")
        self.assertIn("lisinopril", result)
        db.unlink()

    # ------------------------------------------------------------------
    # reload_terms
    # ------------------------------------------------------------------

    def test_reload_clears_cache(self):
        """After reload_terms(), a new DB read should pick up new rows."""
        db = self._make_db([("metformin", "met four min")])
        with patch.object(self.mp, "DB_PATH", db):
            self.mp._load_terms.cache_clear()
            # First load
            self.mp.correct_medical_text("met four min")
            # Now add a new term to the DB
            conn = sqlite3.connect(str(db))
            conn.execute("INSERT INTO terms (term, common_misrecognition) VALUES (?, ?)",
                         ("atorvastatin", "ator vass ta tin"))
            conn.commit()
            conn.close()
            # Reload and check new term is recognised
            self.mp.reload_terms()
            result = self.mp.correct_medical_text("prescribe ator vass ta tin 20mg")
        self.assertIn("atorvastatin", result)
        db.unlink()


if __name__ == "__main__":
    unittest.main()
