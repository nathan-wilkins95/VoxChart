#!/usr/bin/env bash
# VoxChart — macOS launcher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Virtual environment check ──────────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo
  echo "Virtual environment not found. Run setup first:"
  echo
  echo "  python3 -m venv venv"
  echo "  source venv/bin/activate"
  echo "  pip install -r requirements-macos.txt"
  echo
  exit 1
fi

source venv/bin/activate

# ── macOS microphone permission reminder ───────────────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
  echo "[VoxChart] Tip: if the mic doesn't work, go to"
  echo "  System Settings → Privacy & Security → Microphone"
  echo "  and allow Terminal (or your Python app)."
fi

echo "Starting VoxChart..."
python app.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo
  echo "VoxChart exited with error code $EXIT_CODE. Check the output above."
  read -rp "Press Enter to close..."
fi
