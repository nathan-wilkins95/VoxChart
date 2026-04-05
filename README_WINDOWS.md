# VoxChart — Medical Dictation App (Windows)

**Offline AI speech-to-text → chart notes.** Runs Whisper large-v3-turbo on your GPU.

## 📦 One-Click Build & Install

### For Developers (Build EXE)
```powershell
# 1. Double-click build_windows.bat
#    → Creates dist/VoxChart_Setup_v1.0.0.exe (90MB)

# 2. Test the installer
Double-click dist/VoxChart_Setup_v1.0.0.exe
```

### For End Users (Just Run)
```
1. Download VoxChart_Setup_v1.0.0.exe
2. Double-click → Installs to C:\Program Files\VoxChart\
3. Desktop shortcut created
4. Runs first-time setup wizard
```

## 🛠️ Manual Development Setup

```powershell
# Fresh clone
py -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-windows.txt

# Test
test_windows.bat
run_app_windows.bat
```

## 🚀 Features

- **GPU-accelerated** Whisper large-v3-turbo (RTX 4070 = 1-2s latency)
- **First-run wizard** → auto-detects GPU + microphone
- **Medical terms DB** → fixes "met four min" → metformin
- **Live transcript** → real-time display
- **Config saved** → remembers your mic + device choice

## 📋 Packaging Notes

- **90MB single EXE** → no Python install needed
- **medical_terms.db** embedded
- **PyInstaller** → onefile + windowed + hidden console
- **torch cu130** → matches CUDA 13.0 drivers

## Troubleshooting

```
GPU not detected? → nvidia-smi (shows RTX 4070?)
Mic not working? → test_windows.bat
Build fails? → Check venv activation
```

**Ready for GitHub Release!** Upload `dist/VoxChart_Setup_v1.0.0.exe` → users just download + double-click. [file:251]
