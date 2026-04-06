"""epic_exporter.py

Formats VoxChart transcripts into Epic-ready SmartPhrase text and
copies them to the clipboard for direct paste into any Epic note field.

No Epic API or credentials required.

Usage (standalone):
    python epic_exporter.py chart_notes/chart_note.txt

Usage (from app.py):
    from epic_exporter import format_for_epic, copy_to_clipboard
"""

from __future__ import annotations

import re
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path


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


def _score_sentence(sentence: str, patterns: list[str]) -> int:
    """Return count of keyword pattern matches in sentence."""
    s = sentence.lower()
    return sum(1 for p in patterns if re.search(p, s, re.IGNORECASE))


def _clean_transcript(raw: str) -> str:
    """Strip session markers and extra whitespace."""
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if re.match(r"^--- Session (started|stopped)", stripped):
            continue
        lines.append(stripped)
    return " ".join(filter(None, lines))


def _split_into_sentences(text: str) -> list[str]:
    """Naive sentence splitter."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _classify_sentences(sentences: list[str]) -> dict[str, list[str]]:
    """Assign each sentence to the best-matching section."""
    sections: dict[str, list[str]] = {
        "CHIEF COMPLAINT": [],
        "HISTORY OF PRESENT ILLNESS": [],
        "PHYSICAL EXAMINATION": [],
        "ASSESSMENT": [],
        "PLAN": [],
        "ADDITIONAL NOTES": [],
    }

    scorers = [
        ("CHIEF COMPLAINT",            _CC_KEYWORDS),
        ("HISTORY OF PRESENT ILLNESS", _HPI_KEYWORDS),
        ("PHYSICAL EXAMINATION",        _EXAM_KEYWORDS),
        ("ASSESSMENT",                  _ASSESSMENT_KEYWORDS),
        ("PLAN",                         _PLAN_KEYWORDS),
    ]

    for sentence in sentences:
        scores = {name: _score_sentence(sentence, kw) for name, kw in scorers}
        best_section = max(scores, key=scores.get)
        if scores[best_section] == 0:
            best_section = "ADDITIONAL NOTES"
        sections[best_section].append(sentence)

    return sections


def format_for_epic(
    transcript: str,
    provider_name: str = "",
    patient_name: str = "",
    dob: str = "",
    mrn: str = "",
) -> str:
    """
    Format a raw VoxChart transcript into an Epic SmartPhrase-ready note.

    Parameters
    ----------
    transcript    : Raw dictated text (multi-line OK).
    provider_name : Provider's name for signature line.
    patient_name  : Optional patient name for header.
    dob           : Optional date of birth.
    mrn           : Optional MRN.

    Returns
    -------
    Formatted string ready for paste into Epic.
    """
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    cleaned = _clean_transcript(transcript)
    sentences = _split_into_sentences(cleaned)
    sections = _classify_sentences(sentences)

    lines: list[str] = []

    # ── Header ───────────────────────────────────────────────────────────────
    lines.append("=" * 60)
    lines.append("CHART NOTE — VoxChart Offline AI Dictation")
    lines.append(f"Date: {date_str}    Time: {time_str}")
    if patient_name:
        lines.append(f"Patient: {patient_name}")
    if dob:
        lines.append(f"DOB: {dob}")
    if mrn:
        lines.append(f"MRN: {mrn}")
    lines.append("=" * 60)
    lines.append("")

    # ── Sections ─────────────────────────────────────────────────────────────
    section_order = [
        "CHIEF COMPLAINT",
        "HISTORY OF PRESENT ILLNESS",
        "PHYSICAL EXAMINATION",
        "ASSESSMENT",
        "PLAN",
        "ADDITIONAL NOTES",
    ]

    for section in section_order:
        content = sections.get(section, [])
        if not content:
            continue
        lines.append(f"{section}:")
        lines.append("-" * len(section))
        lines.append(" ".join(content))
        lines.append("")

    # ── Signature ────────────────────────────────────────────────────────────
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
    root.update()   # keep clipboard alive
    root.after(500, root.destroy)
    root.mainloop()


def export_to_file(
    formatted: str,
    output_dir: str = "epic_exports",
    filename: str | None = None,
) -> Path:
    """Save the formatted note to an epic_exports/ folder."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"epic_note_{ts}.txt"
    filepath = out / filename
    filepath.write_text(formatted, encoding="utf-8")
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
#  CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python epic_exporter.py <transcript_file.txt>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    raw = src.read_text(encoding="utf-8")
    formatted = format_for_epic(raw, provider_name="Dr. [Name]")

    saved = export_to_file(formatted)
    print(f"\n✅ Epic note saved to: {saved}")
    print("\n" + "=" * 60)
    print(formatted)
    print("=" * 60)

    copy_to_clipboard(formatted)
    print("\n📋 Note copied to clipboard — paste directly into Epic!")
