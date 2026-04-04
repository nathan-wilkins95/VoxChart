# Medical Dictation App — Windows AI-Tech Package

## What changed

- AI-tech app icon added for EXE and desktop shortcut.
- `app.py` updated for GUI-first use and no-terminal launch flow.
- `MedicalDictation.spec` updated to embed the icon and keep the console hidden.
- Batch files now call `venv\Scripts\python.exe` directly instead of relying on activation.
- Desktop shortcut helper added: `create_desktop_shortcut.ps1`.

## Build the clickable app

1. Open PowerShell in this folder.
2. Run:

```powershell
python -m venv venv
.env\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r .equirements-windows.txt
.uild_exe_windows.bat
```

3. After build completes, run:

```powershell
.\create_desktop_shortcut.ps1
```

4. Double-click the **Medical Dictation** desktop icon.

## Result

The user launches the app by clicking the desktop icon and does not need to see PowerShell, Python, or the backend files during normal use.
