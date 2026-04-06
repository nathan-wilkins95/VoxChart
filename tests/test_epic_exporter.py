"""
tests/test_epic_exporter.py
Unit tests for epic_exporter.py
(clipboard test skipped in CI — requires display)
"""
import pytest
from pathlib import Path
from unittest.mock import patch

import epic_exporter as ee


SAMPLE_TRANSCRIPT = """
--- Session started 10:00:00 ---
Patient presents with chest pain that started two days ago.
Blood pressure is 130 over 85. Heart rate is 72.
Assessment: likely musculoskeletal pain.
Plan: ibuprofen 400mg twice daily, follow up in one week.
--- Session stopped 10:05:00 ---
"""


def test_format_for_epic_returns_string():
    result = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    assert isinstance(result, str)
    assert len(result) > 0


def test_format_includes_header_divider():
    result = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    assert "CHART NOTE" in result
    assert "=" * 10 in result


def test_format_includes_provider_name():
    result = ee.format_for_epic(SAMPLE_TRANSCRIPT, provider_name="Dr. Smith")
    assert "Dr. Smith" in result


def test_format_includes_patient_info():
    result = ee.format_for_epic(
        SAMPLE_TRANSCRIPT,
        patient_name="John Doe",
        dob="01/15/1970",
        mrn="123456"
    )
    assert "John Doe" in result
    assert "01/15/1970" in result
    assert "123456" in result


def test_session_markers_stripped():
    result = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    assert "Session started" not in result
    assert "Session stopped" not in result


def test_plan_section_detected():
    result = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    assert "PLAN" in result


def test_assessment_section_detected():
    result = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    assert "ASSESSMENT" in result


def test_export_to_file_creates_file(tmp_path):
    formatted = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    out = ee.export_to_file(formatted, output_dir=str(tmp_path), filename="test_note.txt")
    assert out.exists()
    assert out.read_text(encoding="utf-8") == formatted


def test_export_to_file_auto_filename(tmp_path):
    formatted = ee.format_for_epic(SAMPLE_TRANSCRIPT)
    out = ee.export_to_file(formatted, output_dir=str(tmp_path))
    assert out.exists()
    assert out.name.startswith("epic_note_")


def test_clean_transcript_removes_markers():
    cleaned = ee._clean_transcript(SAMPLE_TRANSCRIPT)
    assert "Session started" not in cleaned
    assert "chest pain" in cleaned
