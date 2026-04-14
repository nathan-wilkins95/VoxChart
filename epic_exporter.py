"""epic_exporter.py

Enhanced Epic clipboard integration for VoxChart.

Features
--------
* Formats transcripts into Epic-ready text with SmartPhrase (.VOXNOTE.) syntax
* Per-section copy support (CC, HPI, Exam, Assessment, Plan)
* Persists a local export history in SQLite (epic_exports/history.db)
* Standalone CLI: python epic_exporter.py <transcript.txt>
"""

from __future__ import annotations

import re
import sys
import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
#  Section detection keywords
# ─────────────────────────────────────────────────────────────────────────────

_CC_KEYWORDS = [
    r"\bchief complaint\b", r"\bpresenting\b", r"\bcomplains of\b",
    r"\bcame in (for|with|because)\b", r"\bhere (for|today for)\b",
    r"\bpresents (with|for)\b",
]

_HPI_KEYWORDS = [
    r"\bhistory of present illness\b", r"\bHPI\b",
    r"\bpatient (is|was|has|reports|denies|states)\b",
    r"\b(started|began|onset|duration|worsened|improved)\b",
]

_EXAM_KEYWORDS = [
    r"\b(physical exam|examination|on exam|vitals)\b",
    r"\b(blood pressure|heart rate|temperature|respiratory rate|oxygen saturation)\b",
    r"\b(lungs (are|reveal|clear)|heart (regular|irregular))\b",
]

_ASSESSMENT_KEYWORDS = [
    r"\b(assessment|impression|diagnosis|diagnoses)\b",
    r"\b(consistent with|likely|probable|rule out)\b",
]

_PLAN_KEYWORDS = [
    r"\b(plan|management|treatment|therapy|follow.up|follow up|referral)\b",
    r"\b(continue|start|stop|increase|decrease|prescribe|order)\b",
    r"\b(will (check|monitor|recheck|repeat|order|refer|schedule))\b",
]

SECTION_ORDER = [
    "CHIEF COMPLAINT",
    "HISTORY OF PRESENT ILLNESS",
    "PHYSICAL EXAMINATION",
    "ASSESSMENT",
    "PLAN",
    "ADDITIONAL NOTES",
]

# SmartPhrase dot-phrase trigger for each section (Epic expands these)
SMARTPHRASE_TRIGGERS = {
    "CHIEF COMPLAINT":            ".VOXCC.",
    "HISTORY OF PRESENT ILLNESS": ".VOXHPI.",
    "PHYSICAL EXAMINATION":       ".VOXEXAM.",
    "ASSESSMENT":                 ".VOXASSESS.",
    "PLAN":                       ".VOXPLAN.",
    "ADDITIONAL NOTES":           ".VOXNOTES.",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _score_sentence(sentence: str, patterns: list[str]) -> int:
    s = sentence.lower()
    return sum(1 for p in patterns if re.search(p, s, re.IGNORECASE))


def _clean_transcript(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if re.match(r"^--- Session (started|stopped)", stripped):
            continue
        lines.append(stripped)
    return " ".join(filter(None, lines))


def _split_into_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _classify_sentences(sentences: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {s: [] for s in SECTION_ORDER}
    scorers = [
        ("CHIEF COMPLAINT",            _CC_KEYWORDS),
        ("HISTORY OF PRESENT ILLNESS", _HPI_KEYWORDS),
        ("PHYSICAL EXAMINATION",        _EXAM_KEYWORDS),
        ("ASSESSMENT",                  _ASSESSMENT_KEYWORDS),
        ("PLAN",                         _PLAN_KEYWORDS),
    ]
    for sentence in sentences:
        scores = {name: _score_sentence(sentence, kw) for name, kw in scorers}
        best = max(scores, key=scores.get)
        sections["ADDITIONAL NOTES" if scores[best] == 0 else best].append(sentence)
    return sections


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_sections(transcript: str) -> dict[str, str]:
    """
    Parse a raw transcript into a dict of {section_name: text}.
    Only sections with content are included.
    """
    cleaned = _clean_transcript(transcript)
    sentences = _split_into_sentences(cleaned)
    classified = _classify_sentences(sentences)
    return {
        section: " ".join(lines)
        for section, lines in classified.items()
        if lines
    }


def format_section(section: str, content: str, smartphrase: bool = False) -> str:
    """
    Format a single section as an Epic-ready block.
    If smartphrase=True, prepend the SmartPhrase dot-trigger.
    """
    trigger = SMARTPHRASE_TRIGGERS.get(section, "")
    header = f"{section}:"
    sep = "-" * len(section)
    body = content.strip()
    if smartphrase and trigger:
        return f"{trigger}\n{header}\n{sep}\n{body}\n"
    return f"{header}\n{sep}\n{body}\n"


def format_for_epic(
    transcript: str,
    provider_name: str = "",
    patient_name: str = "",
    dob: str = "",
    mrn: str = "",
    encounter_id: str = "",
    visit_type: str = "",
    smartphrase: bool = False,
) -> str:
    """
    Format a VoxChart transcript into a full Epic-ready chart note.

    Parameters
    ----------
    transcript    : Raw dictated text.
    provider_name : Provider name for signature.
    patient_name  : Optional patient name.
    dob           : Optional date of birth.
    mrn           : Optional MRN.
    encounter_id  : Optional Epic encounter ID.
    visit_type    : Optional visit type (e.g. 'Office Visit').
    smartphrase   : If True, prefix each section with its SmartPhrase trigger.
    """
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    sections = parse_sections(transcript)
    lines: list[str] = []

    # Header
    lines.append("=" * 60)
    lines.append("CHART NOTE — VoxChart Offline AI Dictation")
    lines.append(f"Date: {date_str}    Time: {time_str}")
    if patient_name:  lines.append(f"Patient:      {patient_name}")
    if dob:           lines.append(f"DOB:          {dob}")
    if mrn:           lines.append(f"MRN:          {mrn}")
    if encounter_id:  lines.append(f"Encounter ID: {encounter_id}")
    if visit_type:    lines.append(f"Visit Type:   {visit_type}")
    lines.append("=" * 60)
    lines.append("")

    # Sections in canonical order
    for section in SECTION_ORDER:
        content = sections.get(section)
        if not content:
            continue
        lines.append(format_section(section, content, smartphrase=smartphrase))

    # Signature
    lines.append("-" * 60)
    if provider_name:
        lines.append(f"Electronically signed by: {provider_name}")
    lines.append(f"Date/Time: {date_str} {time_str}")
    lines.append("Dictated via VoxChart Offline AI")
    lines.append("-" * 60)

    return "\n".join(lines)


def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard using tkinter (no extra deps)."""
    root = tk.Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    root.after(500, root.destroy)
    root.mainloop()


def export_to_file(
    formatted: str,
    output_dir: str = "epic_exports",
    filename: Optional[str] = None,
) -> Path:
    """Save the formatted note to epic_exports/."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"epic_note_{ts}.txt"
    filepath = out / filename
    filepath.write_text(formatted, encoding="utf-8")
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
#  Export history log (SQLite)
# ─────────────────────────────────────────────────────────────────────────────

_HISTORY_DB = Path("epic_exports") / "history.db"


def _init_history_db() -> None:
    Path("epic_exports").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_HISTORY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS export_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            exported_at TEXT    NOT NULL,
            patient_name TEXT,
            mrn         TEXT,
            encounter_id TEXT,
            method      TEXT,   -- 'clipboard' | 'file' | 'fhir'
            file_path   TEXT,
            note_preview TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_export(
    patient_name: str = "",
    mrn: str = "",
    encounter_id: str = "",
    method: str = "clipboard",
    file_path: str = "",
    note_preview: str = "",
) -> None:
    """Record an export event in the local history database."""
    _init_history_db()
    conn = sqlite3.connect(str(_HISTORY_DB))
    conn.execute(
        """
        INSERT INTO export_log
            (exported_at, patient_name, mrn, encounter_id, method, file_path, note_preview)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            patient_name or "",
            mrn or "",
            encounter_id or "",
            method,
            file_path or "",
            note_preview[:300] if note_preview else "",
        ),
    )
    conn.commit()
    conn.close()


def list_exports(limit: int = 50) -> list[dict]:
    """Return recent export history records."""
    _init_history_db()
    conn = sqlite3.connect(str(_HISTORY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM export_log ORDER BY exported_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python epic_exporter.py <transcript_file.txt> [--smartphrase]")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    use_sp = "--smartphrase" in sys.argv
    raw = src.read_text(encoding="utf-8")
    formatted = format_for_epic(raw, provider_name="Dr. [Name]", smartphrase=use_sp)

    saved = export_to_file(formatted)
    log_export(method="file", file_path=str(saved), note_preview=formatted)

    print(f"\n✅ Epic note saved to: {saved}")
    print("\n" + "=" * 60)
    print(formatted)
    print("=" * 60)

    copy_to_clipboard(formatted)
    print("\n📋 Note copied to clipboard — paste directly into Epic!")
