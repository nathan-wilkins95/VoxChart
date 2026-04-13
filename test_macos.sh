#!/usr/bin/env bash
# VoxChart — macOS environment test
# Run this before launching the app to confirm all dependencies work.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "=== VoxChart macOS Environment Test ==="
echo

# ── Python version ─────────────────────────────────────────────────────────
echo "[1] Python version:"
python3 --version
echo

# ── faster-whisper (CPU int8 — no CUDA on macOS) ───────────────────────────
echo "[2] faster-whisper CPU test (small.en, int8)..."
python3 - <<'EOF'
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8")
print("  faster-whisper OK — CPU int8")
EOF
echo

# ── sounddevice / microphone list ─────────────────────────────────────────
echo "[3] sounddevice — available input devices:"
python3 - <<'EOF'
import sounddevice as sd
devices = sd.query_devices()
inputs = [(i, d['name']) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
if inputs:
    for idx, name in inputs:
        print(f"  [{idx}] {name}")
else:
    print("  WARNING: No input devices found. Check microphone permissions.")
    print("  System Settings → Privacy & Security → Microphone → allow Terminal")
EOF
echo

# ── customtkinter ──────────────────────────────────────────────────────────
echo "[4] customtkinter import test..."
python3 -c "import customtkinter; print('  customtkinter OK —', customtkinter.__version__)"
echo

# ── numpy / soundfile ─────────────────────────────────────────────────────
echo "[5] numpy + soundfile..."
python3 -c "import numpy, soundfile; print('  numpy', numpy.__version__, '| soundfile OK')"
echo

echo "=== All tests passed. Run: bash run_app_macos.sh ==="
