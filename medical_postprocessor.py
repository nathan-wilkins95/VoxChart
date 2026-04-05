import re
import sqlite3
from pathlib import Path

DB_PATH = "medical_terms.db"


def load_terms():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT term, common_misrecognition FROM terms")
    rows = cur.fetchall()
    conn.close()
    # Map misrecognition -> correct term, plus direct term boosts
    mis_to_correct = {}
    correct_terms = set()
    for term, mis in rows:
        correct_terms.add(term.lower())
        if mis:
            mis_to_correct[mis.lower()] = term
    return mis_to_correct, correct_terms


MIS_TO_CORRECT, CORRECT_TERMS = load_terms()


def correct_medical_text(text: str) -> str:
    text_lower = text.lower()
    # Simple phrase replacements for known misrecognitions
    for mis, correct in MIS_TO_CORRECT.items():
        if mis in text_lower:
            # Case-insensitive replace, preserving surrounding context
            text = re.sub(re.escape(mis), correct, text, flags=re.IGNORECASE)

    # Optional: you can add more sophisticated rules here
    # e.g., fix "rails" -> "rales" only in respiratory context
    return text
