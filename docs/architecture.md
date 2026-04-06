# VoxChart Architecture

This document maps every module in the codebase and how they connect.

---

## Module Map

```
app.py  (main window, entry point)
├── splash.py                  Startup splash screen (model load progress)
├── about_dialog.py            About window (version, credits, links)
├── settings.py                Settings window + load_config / save_config
├── version.py                 APP_VERSION constant
├── dictation_engine.py        Whisper recording + transcription engine
│   ├── medical_postprocessor.py  Corrects Whisper misrecognitions via SQLite DB
│   └── training_corpus.py        Saves audio+transcript pairs, fine-tune runner
├── session_history.py         SQLite session log (start, stop, search, export)
├── epic_exporter.py           Formats transcript for Epic EMR, clipboard + file
├── templates.py               Built-in + custom note templates (JSON-backed)
├── autosave.py                Background autosave thread + crash recovery
├── updater.py                 GitHub Releases API version check (bg thread)
├── crash_reporter.py          Logging setup, exception hook, bug report dialog
├── shortcut_utils.py          Desktop shortcut creation (Windows/Linux/macOS)
└── build_medical_db.py        One-time script to seed medical_terms.db
```

---

## Data Flow: Dictation Session

```
Microphone
    ↓
 DictationEngine._sd_callback()
    ↓  (audio chunks via sounddevice)
 DictationEngine._process_audio()
    ↓  (faster-whisper transcription)
 MedicalPostprocessor.correct_medical_text()
    ↓  (corrected text segment)
 app.py → append_transcript()  →  CTkTextbox (live display)
    ↓
 AutoSaver (every N seconds writes to disk)
    ↓
 session_history.stop_session()  (on Stop — saves word count, duration)
```

---

## Data Flow: Update Check

```
app._post_launch()
    ↓
check_for_update()  [background thread]
    ↓  (urllib → GitHub API)
_fetch_latest() → {tag, url, notes}
    ↓
on_update_available(version, url, notes)
    ↓
app._build_update_banner()  →  UpdateNotesDialog (on click)
```

---

## Data Flow: Epic Export

```
CTkTextbox (transcript)
    ↓
EpicExportDialog (provider name, patient, DOB, MRN)
    ↓
format_for_epic()  →  formatted note string
    ↓  ├── copy_to_clipboard()
       └── export_to_file()  →  chart_notes/
```

---

## Key Files & Storage

| File / Dir | Purpose |
|---|---|
| `config.json` | User settings (device, mic, model, language, font size) |
| `medical_terms.db` | SQLite — medical term corrections |
| `sessions.db` | SQLite — session history (start time, duration, word count, file path) |
| `chart_notes/` | Output `.txt` files from each dictation session |
| `training_corpus/` | Audio + transcript pairs for Whisper fine-tuning |
| `logs/` | Rolling log files (crash_reporter.py) |
| `custom_templates.json` | User-defined note templates |

---

## Adding a New Module

1. Create `your_module.py` in the root.
2. Add a docstring describing its purpose.
3. Import it in `app.py` only if it adds UI or startup behavior.
4. Add tests in `tests/test_your_module.py`.
5. Update this document and `CONTRIBUTING.md` if the data flow changes.
