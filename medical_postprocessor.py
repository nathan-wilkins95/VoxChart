"""
medical_postprocessor.py
Corrects Whisper misrecognitions using the medical_terms SQLite DB.
Gracefully handles missing DB (no crash, just passthrough).
"""
from __future__ import annotations
import re
import sqlite3
import logging
from pathlib import Path
from functools import lru_cache

DB_PATH = Path("medical_terms.db")
logger  = logging.getLogger("voxchart.postprocessor")


@lru_cache(maxsize=1)
def _load_terms() -> tuple[dict, set]:
    """
    Load correction table from SQLite DB.
    Returns (mis_to_correct, correct_terms_set).
    Cached after first call so DB is only read once per session.
    """
    if not DB_PATH.exists():
        logger.debug("medical_terms.db not found — postprocessor running in passthrough mode")
        return {}, set()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur  = conn.cursor()
        cur.execute("SELECT term, common_misrecognition FROM terms")
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.warning("Failed to load medical terms DB: %s", e)
        return {}, set()

    mis_to_correct: dict[str, str] = {}
    correct_terms:  set[str]       = set()
    for term, mis in rows:
        if term:
            correct_terms.add(term.lower())
        if mis and term:
            mis_to_correct[mis.lower()] = term
    logger.info("Loaded %d misrecognition corrections, %d terms",
                len(mis_to_correct), len(correct_terms))
    return mis_to_correct, correct_terms


def reload_terms():
    """Force reload of the DB (call after adding new terms in the UI)."""
    _load_terms.cache_clear()
    _load_terms()


def correct_medical_text(text: str) -> str:
    """
    Apply misrecognition corrections to a Whisper transcript segment.
    Safe to call even if the DB does not exist.
    """
    if not text.strip():
        return text

    mis_to_correct, _ = _load_terms()
    if not mis_to_correct:
        return text  # passthrough

    for mis, correct in mis_to_correct.items():
        # Whole-word replacement only (avoids mangling substrings)
        pattern = r'(?<![\w-])' + re.escape(mis) + r'(?![\w-])'
        text = re.sub(pattern, correct, text, flags=re.IGNORECASE)

    return text
