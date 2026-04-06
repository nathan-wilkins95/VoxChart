"""
dictation_engine.py
Captures audio, transcribes with Faster-Whisper, saves corpus pairs.
"""
from __future__ import annotations
import os
import sys
import threading
import queue
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
from medical_postprocessor import correct_medical_text

logger = logging.getLogger("voxchart.engine")

# Whisper always wants 16 kHz mono
SAMPLE_RATE   = 16000
BUFFER_SECONDS = 5   # flush to Whisper every N seconds


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


class DictationEngine:
    def __init__(
        self,
        model_size: str  = "large-v3-turbo",
        device: str      = "cpu",
        compute_type: str = "int8",
        output_dir: str  = "chart_notes",
        corpus_dir: str  = "training_corpus",
        medical_prompt: str | None = None,
        language: str    = "en",
        mic_index: int | None = None,
    ):
        self.model_size    = model_size
        self.device        = device
        self.compute_type  = compute_type
        self.output_dir    = Path(output_dir)
        self.corpus_dir    = Path(corpus_dir)
        self.language      = language
        self.mic_index     = mic_index  # None = sounddevice default
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.corpus_dir.mkdir(parents=True, exist_ok=True)

        self.medical_prompt = medical_prompt or (
            "You are transcribing a clinical note for a medical chart. "
            "Preserve drug names, dosages, and medical terminology exactly."
        )

        self.model             = None
        self.audio_queue       = queue.Queue()
        self.stop_event        = threading.Event()
        self.transcribe_thread = None
        self.stream            = None
        self.is_running        = False
        self._input_rate       = None   # detected at stream-open time
        self._input_channels   = None

        self.on_text_callback   = None
        self.on_status_callback = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_status(self, msg: str):
        logger.info(msg)
        if self.on_status_callback:
            self.on_status_callback(msg)

    def _emit_text(self, text: str):
        if self.on_text_callback:
            self.on_text_callback(text)

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _get_local_model_dir(self) -> Path | None:
        for candidate in [
            resource_path("models", self.model_size),
            Path("models") / self.model_size,
            Path("whisper-medical-finetuned"),   # fine-tuned model
        ]:
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None

    def load_model(self):
        local_dir = self._get_local_model_dir()
        t0 = time.time()
        model_ref = str(local_dir) if local_dir else self.model_size
        self._log_status(f"Loading model '{model_ref}' on {self.device}...")
        self.model = WhisperModel(
            model_ref,
            device=self.device,
            compute_type=self.compute_type,
            download_root=str(Path.home() / ".cache" / "whisper"),
        )
        self._log_status(f"Model loaded in {time.time() - t0:.1f}s")

    # ------------------------------------------------------------------
    # Audio helpers
    # ------------------------------------------------------------------

    def _detect_input_rate(self) -> tuple[int, int]:
        """
        Query sounddevice for the default (or chosen) mic's native sample
        rate and channel count.  Falls back to 44100 / 1 if anything fails.
        """
        try:
            info = sd.query_devices(self.mic_index, kind="input")
            rate = int(info["default_samplerate"])
            ch   = min(int(info["max_input_channels"]), 2)
            return rate, ch
        except Exception as e:
            logger.warning("Could not query device info: %s — using 44100/1", e)
            return 44100, 1

    def _to_mono_16k(self, indata: np.ndarray, input_rate: int) -> np.ndarray:
        """Convert any-rate, any-channel float32 array to 16 kHz mono."""
        # Stereo -> mono
        if indata.ndim > 1 and indata.shape[1] > 1:
            audio = indata.mean(axis=1)
        else:
            audio = indata.flatten()
        # Downsample if needed (integer ratio preferred; else simple decimate)
        if input_rate != SAMPLE_RATE:
            ratio = input_rate / SAMPLE_RATE
            n_out = int(len(audio) / ratio)
            indices = (np.arange(n_out) * ratio).astype(int)
            indices = np.clip(indices, 0, len(audio) - 1)
            audio = audio[indices]
        return audio

    def _sd_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("Audio status: %s", status)
        mono16k = self._to_mono_16k(indata, self._input_rate)
        pcm = (mono16k * 32767).astype(np.int16).tobytes()
        self.audio_queue.put(pcm)

    # ------------------------------------------------------------------
    # Transcription loop
    # ------------------------------------------------------------------

    def _transcribe_loop(self, output_file: str):
        audio_buffer   = []
        buffer_duration = 0.0
        last_flush     = time.time()

        with open(output_file, "a", encoding="utf-8") as f:
            while not self.stop_event.is_set() or not self.audio_queue.empty():
                try:
                    data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                audio_buffer.append(data)
                buffer_duration += len(data) / (SAMPLE_RATE * 2)

                flush_ready = (
                    buffer_duration >= BUFFER_SECONDS or
                    (time.time() - last_flush > 4 and buffer_duration > 1)
                )
                if not flush_ready:
                    continue

                raw         = b"".join(audio_buffer)
                audio_array = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                audio_buffer    = []
                buffer_duration = 0.0
                last_flush      = time.time()

                try:
                    segments, _ = self.model.transcribe(
                        audio_array,
                        language=self.language,
                        initial_prompt=self.medical_prompt,
                        beam_size=5,
                        word_timestamps=True,
                        condition_on_previous_text=True,
                        vad_filter=True,
                    )
                except Exception as e:
                    self._log_status(f"Transcription error: {e}")
                    continue

                text_parts = [
                    seg.text.strip()
                    for seg in segments
                    if getattr(seg, "no_speech_prob", 0) <= 0.9
                ]

                if text_parts:
                    raw_text       = " ".join(text_parts)
                    corrected_text = correct_medical_text(raw_text)
                    f.write(corrected_text + "\n")
                    f.flush()
                    self._emit_text(corrected_text)
                    self._save_corpus_pair(audio_array, corrected_text)

    def _save_corpus_pair(self, audio_array: np.ndarray, text: str):
        """Save .wav + .txt training pair to corpus_dir."""
        try:
            ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
            hid = hashlib.sha256(text.encode()).hexdigest()[:8]
            wav_path = self.corpus_dir / f"{ts}_{hid}.wav"
            txt_path = self.corpus_dir / f"{ts}_{hid}.txt"
            sf.write(str(wav_path), audio_array, SAMPLE_RATE)
            txt_path.write_text(text + "\n", encoding="utf-8")
            logger.debug("Corpus pair saved: %s", wav_path.name)
        except Exception as e:
            logger.warning("Corpus save failed: %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, output_file: str):
        if self.is_running:
            return
        if self.model is None:
            self.load_model()

        self._input_rate, self._input_channels = self._detect_input_rate()
        logger.info("Opening mic: device=%s rate=%d ch=%d",
                    self.mic_index, self._input_rate, self._input_channels)

        self.stop_event.clear()
        self.audio_queue = queue.Queue()
        self.is_running  = True

        self.stream = sd.InputStream(
            samplerate=self._input_rate,
            channels=self._input_channels,
            device=self.mic_index,
            dtype="float32",
            blocksize=int(self._input_rate * 0.25),  # 250 ms blocks
            callback=self._sd_callback,
        )
        self.stream.start()

        self.transcribe_thread = threading.Thread(
            target=self._transcribe_loop,
            args=(output_file,),
            daemon=True,
        )
        self.transcribe_thread.start()
        self._log_status("Dictation started.")

    def stop(self):
        if not self.is_running:
            return
        self.stop_event.set()
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.transcribe_thread:
            self.transcribe_thread.join(timeout=3.0)
        self.is_running = False
        self._log_status("Dictation stopped.")
