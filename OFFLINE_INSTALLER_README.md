# VoxChart fully offline installer

This build flow now supports a truly offline first run by bundling a local faster-whisper model directory inside the packaged app. [file:250]

## Required local model folder
Before building, place the exported model here:

```text
models\large-v3-turbo\
```

The updated engine checks for a bundled model at `models\large-v3-turbo` first, and only falls back to cache/download if that folder is missing. [file:250]

## Files to replace
- `dictation_engine.py`
- `build_windows.bat`
- `VoxChartInstaller.iss`

## Build
1. Install Inno Setup 6.
2. Put your model folder in `models\large-v3-turbo`.
3. Run `build_windows.bat`.
4. Output: `dist\VoxChart_Setup_v1.0.0.exe`.

## Result
The installer is offline, and the app can also complete first launch offline because the Whisper model is bundled into the packaged executable. [file:250]
