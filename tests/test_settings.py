"""
tests/test_settings.py
Unit tests for settings.py
"""
import json
import pytest
from pathlib import Path

import settings as s


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    cfg_path = tmp_path / "voxchart_config.json"
    monkeypatch.setattr(s, "CONFIG_FILE", cfg_path)
    return cfg_path


def test_load_config_returns_defaults_when_no_file():
    cfg = s.load_config()
    assert cfg["font_size"] == 13
    assert cfg["autosave_interval"] == 60
    assert cfg["theme"] == "dark"
    assert cfg["model_size"] == "large-v3-turbo"
    assert cfg["language"] == "en"


def test_save_and_reload_config(tmp_path):
    cfg = s.load_config()
    cfg["font_size"] = 16
    cfg["theme"] = "light"
    s.save_config(cfg)
    reloaded = s.load_config()
    assert reloaded["font_size"] == 16
    assert reloaded["theme"] == "light"


def test_save_config_writes_valid_json(tmp_path):
    cfg = s.load_config()
    s.save_config(cfg)
    from settings import CONFIG_FILE
    data = json.loads(CONFIG_FILE.read_text())
    assert "font_size" in data


def test_load_config_merges_with_defaults(tmp_path):
    from settings import CONFIG_FILE
    # Write a partial config (missing most keys)
    CONFIG_FILE.write_text(json.dumps({"font_size": 18}), encoding="utf-8")
    cfg = s.load_config()
    assert cfg["font_size"] == 18          # overridden
    assert cfg["theme"] == "dark"          # default filled in
    assert cfg["autosave_interval"] == 60  # default filled in


def test_defaults_dict_has_required_keys():
    required = ["font_size", "autosave_interval", "default_template",
                "model_size", "language", "theme", "device",
                "compute_type", "mic_index", "mic_name", "first_run_complete"]
    for key in required:
        assert key in s.DEFAULTS, f"Missing default key: {key}"
