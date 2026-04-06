# Changelog

All notable changes to VoxChart are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.7.0] - 2026-04-06
### Added
- `version_info.txt` — Windows EXE metadata (product name, version, copyright)
- `installer/voxchart.iss` — Inno Setup script to build `VoxChart_Setup.exe`
- `CHANGELOG.md` — this file
- `tests/test_settings.py` — unit tests for settings module
- `tests/test_epic_exporter.py` — unit tests for Epic export formatting
- `.github/workflows/release.yml` — auto-publish GitHub Release on version tag

---

## [1.6.1] - 2026-04-06
### Added
- `tests/` directory with full unit test suite
- `tests/test_autosave.py` — AutoSaver and crash recovery tests
- `tests/test_templates.py` — built-in and custom template tests
- `tests/test_session_history.py` — session DB CRUD tests
- `.github/workflows/build.yml` — GitHub Actions CI on every push
### Updated
- `requirements-windows.txt` — added `packaging`, `transformers`, `datasets`, `accelerate`
- `MedicalDictation.spec` — added v1.6 modules and HuggingFace imports

---

## [1.6.0] - 2026-04-06
### Added
- `version.py` — single source of truth for `APP_VERSION`
- `settings.py` — full Settings window (theme, font size, auto-save interval, model, language, device)
- `autosave.py` — periodic auto-save with crash-detection flag and recovery on startup
- `training_corpus.py` — HuggingFace Whisper fine-tune pipeline with `on_progress` callback
- `README.md` — full project README with features, quickstart, shortcuts, troubleshooting
- `build.bat` — unified 5-option build menu
### Updated
- `app.py` — wired to `settings.py`, `autosave.py`, `version.py`; added ⚙ Settings + 🎤 Fine-tune buttons; crash recovery on startup; font size from config

---

## [1.5.0] - 2026-04-06
### Added
- Auto-updater (`updater.py`) — checks GitHub Releases on startup, shows update banner
- Session history sidebar — SQLite-backed session browser with load/delete
- Live waveform visualizer — real-time audio level bars during recording
- Note templates — SOAP, HPI, Discharge Summary, Procedure Note, Follow-Up, Emergency
- Custom template save/load
- Keyboard shortcuts (Ctrl+Space, Ctrl+S, Ctrl+E, Ctrl+O, Esc, F1, F5)

---

## [1.4.1] - 2026-04-06
### Added
- Code signing scripts (`sign_exe.ps1`, `create_self_signed_cert.ps1`)
- `build_exe_windows.bat` auto-signs after build if cert is present

---

## [1.4.0] - 2026-04-06
### Added
- Epic EHR export (`epic_exporter.py`) — formats transcript into SmartPhrase-ready note, copies to clipboard
- Epic Export dialog with provider/patient/MRN fields

---

## [1.3.0] - 2026-04-06
### Added
- Crash reporter (`crash_reporter.py`) — structured rotating log, bug report dialog, log viewer
- Desktop shortcut utility (`shortcut_utils.py`) — auto-creates shortcut on first run

---

## [1.2.0] - 2026-04-06
### Added
- Medical terms database (`build_medical_db.py`) — SQLite DB of 500+ terms
- Medical post-processor (`medical_postprocessor.py`) — corrects misrecognized terms in transcript
- Medical Terms Manager UI window

---

## [1.1.0] - 2026-04-06
### Added
- Onboarding wizard — 2-step setup (GPU/CPU selection + microphone)
- Mic test button with 3-second live dB level display
- Config persistence (`voxchart_config.json`)

---

## [1.0.0] - 2026-04-06
### Added
- Initial release
- Faster-Whisper transcription (large-v3-turbo)
- CustomTkinter UI with live transcript display
- GPU (CUDA) and CPU support
- Save As and Open Folder actions
