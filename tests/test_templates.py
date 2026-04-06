"""
tests/test_templates.py
Unit tests for templates.py
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

import templates


def test_all_templates_returns_dict():
    t = templates.all_templates()
    assert isinstance(t, dict)
    assert len(t) > 0


def test_builtin_templates_present():
    t = templates.all_templates()
    for name in ["SOAP Note", "HPI", "Discharge Summary",
                 "Procedure Note", "Follow-Up Visit", "Emergency Note"]:
        assert name in t, f"Missing built-in template: {name}"


def test_get_template_returns_body():
    body = templates.get_template("SOAP Note")
    assert body
    assert "Subjective" in body or "SUBJECTIVE" in body


def test_get_template_missing_returns_none():
    assert templates.get_template("NonExistentTemplate_XYZ") is None


def test_add_custom_template(tmp_path, monkeypatch):
    custom_file = tmp_path / "custom_templates.json"
    monkeypatch.setattr(templates, "CUSTOM_TEMPLATES_FILE", custom_file)
    templates.add_custom_template("My Test Template", "Body text here.")
    data = json.loads(custom_file.read_text())
    assert "My Test Template" in data
    assert data["My Test Template"] == "Body text here."


def test_custom_template_appears_in_all(tmp_path, monkeypatch):
    custom_file = tmp_path / "custom_templates.json"
    monkeypatch.setattr(templates, "CUSTOM_TEMPLATES_FILE", custom_file)
    templates.add_custom_template("CustomCard", "Cardiology note.")
    all_t = templates.all_templates()
    assert "CustomCard" in all_t
