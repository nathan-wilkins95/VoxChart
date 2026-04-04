import threading
import queue
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from faster_whisper import WhisperModel
from medical_postprocessor import correct_medical_text

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 4000

class DictationEngine:
    def __init__(
        self,
        model_size="large-v3-turbo",
        device="cuda",
        compute_type="float16",
        output_dir="chart_notes",
        corpus_dir="training_corpus",
        medical_prompt=None
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.output_dir = Path(output_dir)
        self.corpus_dir = Path(corpus_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.corpus_dir.mkdir(parents=True, exist_ok=True)

        self.medical_prompt = medical_prompt or (
            "You are transcribing a clinical note for a medical chart. "
            "Preserve drug names, dosages, and medical terminology exactly."
        )

        self.model = None
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.transcribe_thread = None
        self.stream = None
        self.is_running = False

        self.on_text_callback = None
        self.on_status_callback = None

    def load_model(self):
        if self.model is not None:
            return
        self._log_status(f"Loading model: {self.model_size} on {self.device}...")
        t0 = time.time()
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=str(Path.home() / ".cache" / "whisper")
        )
        self._log_status(f"Model loaded in {time.time() - t0:.1f}s")

    def _log_status(self, msg: str):
        if self.on_status_callback:
            self.on_status_callback(msg)

    def _emit_text(self, text: str):
        if self.on_text_callback:
            self.on_text_callback(text)

    def _sd_callback(self, indata, frames, time_info, status):
        if status:
            self._log_status(f"Audio warning: {status}")
        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        self.audio_queue.put(pcm)

    def _transcribe_loop(self, output_file: str):
        audio_buffer = []
        buffer_duration = 0.0
        last_flush_time = time.time()
        BUFFER_SECONDS = 15

        with open(output_file, "a", encoding="utf-8") as f:
            while not self.stop_event.is_set() or not self.audio_queue.empty():
                try:
                    data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                audio_buffer.append(data)
                buffer_duration += len(data) / (SAMPLE_RATE * 2)

                flush_ready = (
                    buffer_duration >= BUFFER_SECONDS
                    or (time.time() - last_flush_time > 8 and buffer_duration > 3)
                )
                if not flush_ready:
                    continue

                raw = b"".join(audio_buffer)
                audio_array = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                audio_buffer = []
                buffer_duration = 0.0
                last_flush_time = time.time()

                try:
                    segments, _ = self.model.transcribe(
                        audio_array,
                        language="en",
                        initial_prompt=self.medical_prompt,
                        beam_size=5,
                        word_timestamps=True,
                        condition_on_previous_text=True,
                        vad_filter=True
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
                    raw_text = " ".join(text_parts)
                    corrected_text = correct_medical_text(raw_text)
                    f.write(corrected_text + "\n")
                    f.flush()
                    self._emit_text(corrected_text)

                    import hashlib
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    hid = hashlib.sha256(corrected_text.encode()).hexdigest()[:8]
                    sf.write(str(self.corpus_dir / f"{ts}_{hid}.wav"), audio_array, SAMPLE_RATE)
                    (self.corpus_dir / f"{ts}_{hid}.txt").write_text(corrected_text + "\n", encoding="utf-8")

    def start(self, output_file: str):
        if self.is_running:
            return
        if self.model is None:
            self.load_model()

        self.stop_event.clear()
        self.audio_queue = queue.Queue()
        self.is_running = True

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=self._sd_callback
        )
        self.stream.start()

        self.transcribe_thread = threading.Thread(
            target=self._transcribe_loop,
            args=(output_file,),
            daemon=True
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