"""
tests/test_dictation_engine.py
Unit tests for DictationEngine (no real audio/model required).
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path

from dictation_engine import DictationEngine, SAMPLE_RATE


@pytest.fixture
def engine(tmp_path):
    eng = DictationEngine(
        model_size="tiny",
        device="cpu",
        compute_type="int8",
        output_dir=str(tmp_path / "notes"),
        corpus_dir=str(tmp_path / "corpus"),
        language="en",
    )
    return eng


def test_engine_init_creates_dirs(tmp_path):
    eng = DictationEngine(
        output_dir=str(tmp_path / "notes"),
        corpus_dir=str(tmp_path / "corpus"),
    )
    assert (tmp_path / "notes").exists()
    assert (tmp_path / "corpus").exists()


def test_engine_language_default():
    eng = DictationEngine()
    assert eng.language == "en"


def test_engine_language_custom():
    eng = DictationEngine(language="es")
    assert eng.language == "es"


def test_to_mono_16k_stereo_downsamples(engine):
    """48 kHz stereo -> 16 kHz mono."""
    stereo = np.random.randn(48000, 2).astype(np.float32)  # 1 second at 48 kHz
    result = engine._to_mono_16k(stereo, input_rate=48000)
    assert result.ndim == 1
    expected_len = int(48000 / 3)  # 16000
    assert abs(len(result) - expected_len) <= 2


def test_to_mono_16k_already_16k(engine):
    mono = np.random.randn(16000).astype(np.float32)
    result = engine._to_mono_16k(mono.reshape(-1, 1), input_rate=16000)
    assert len(result) == 16000


def test_save_corpus_pair_creates_files(engine, tmp_path):
    audio = np.zeros(16000, dtype=np.float32)
    engine._save_corpus_pair(audio, "patient has chest pain")
    wav_files = list(engine.corpus_dir.glob("*.wav"))
    txt_files = list(engine.corpus_dir.glob("*.txt"))
    assert len(wav_files) == 1
    assert len(txt_files) == 1
    assert "patient has chest pain" in txt_files[0].read_text()


def test_stop_when_not_running_is_safe(engine):
    """stop() on a never-started engine should not raise."""
    engine.stop()  # should not raise


def test_detect_input_rate_fallback(engine):
    """Should fall back to 44100/1 if device query fails."""
    with patch("sounddevice.query_devices", side_effect=Exception("no device")):
        rate, ch = engine._detect_input_rate()
    assert rate == 44100
    assert ch == 1
