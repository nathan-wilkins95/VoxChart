# VoxChart — macOS Setup

## Requirements

- macOS 12 Monterey or later (Intel or Apple Silicon)
- Python 3.10–3.12 — install via [python.org](https://python.org) or Homebrew:
  ```bash
  brew install python@3.11
  ```
- **PortAudio** (required by `sounddevice`):
  ```bash
  brew install portaudio
  ```

> **GPU note:** CUDA is not available on macOS. VoxChart runs on **CPU (int8)** automatically.  
> Apple Silicon (M1/M2/M3) MPS support is not yet available in faster-whisper/CTranslate2 — CPU int8 is the current best option and still performs well.

---

## Setup

Open Terminal in the VoxChart folder:

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements-macos.txt
```

---

## Test first

```bash
bash test_macos.sh
```

This confirms Python, faster-whisper (CPU), sounddevice, and customtkinter all work correctly.  
If microphone devices show as empty, see the **Microphone Permissions** section below.

---

## Run the app

```bash
bash run_app_macos.sh
```

Or manually:

```bash
source venv/bin/activate
python app.py
```

---

## Microphone Permissions

macOS requires explicit permission for Terminal (and Python) to access the microphone.

1. Open **System Settings → Privacy & Security → Microphone**
2. Enable access for **Terminal** (or **Python**, if it appears separately)
3. Restart Terminal and re-run the app

If you built a `.app` bundle with PyInstaller, add the `NSMicrophoneUsageDescription` key to your `Info.plist`.

---

## Build a .app bundle (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name VoxChart app.py
```

The app bundle will appear in `dist/VoxChart.app`.  
To sign and notarize for distribution, see Apple's [Notarizing macOS Software](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution) docs.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Space` | Start / Stop dictation |
| `Ctrl+S` | Save As |
| `Ctrl+E` | Copy to Epic |
| `Ctrl+O` | Open output folder |
| `Esc` | Clear transcript |
| `F1` | Keyboard shortcut help |
| `F5` | Refresh microphone list |

> **macOS note:** `Ctrl` shortcuts use the Control key, not Command (`⌘`), because customtkinter/tkinter uses `Control` bindings cross-platform.

---

## Notes

- The `medical_terms.db` file must stay in the same folder as `app.py`
- Model files are cached in `~/.cache/whisper` after first download
- Transcripts are saved to `chart_notes/chart_note.txt` by default
- Log files are written to `~/Library/Logs/VoxChart/` on macOS
