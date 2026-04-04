# Building the VoxChart Installer

## Prerequisites
- [Inno Setup 6+](https://jrsoftware.org/isinfo.php) installed on Windows
- All Python dependencies installed in your venv

## Steps

### 1. Build the executable
```cmd
cd C:\medical_dictation_windows_final
venv_new\Scripts\activate
pyinstaller --onefile --windowed --icon=assets\icon.ico --name="VoxChart" app.py
```

### 2. Pre-build the medical terms database
```cmd
python build_medical_db.py
```
This creates `medical_terms.db` in the project root.

### 3. Compile the installer
- Open **Inno Setup Compiler**
- File → Open → select `installer/VoxChart.iss`
- Build → Compile (or press F9)
- Output: `installer/output/VoxChart_Setup_v1.0.0.exe`

## What the installer does
- Installs `VoxChart.exe` to `%ProgramFiles%\VoxChart`
- Bundles `medical_terms.db` (no first-run DB setup needed)
- Creates a desktop shortcut (optional, checked by default)
- Creates a Start Menu entry
- Includes a one-click uninstaller
- Launches VoxChart immediately after install

## Notes
- The Whisper AI model (~800MB) is **not** bundled — it downloads automatically
  on first launch with a progress dialog.
- The installer itself will be ~200-250MB depending on dependencies.
