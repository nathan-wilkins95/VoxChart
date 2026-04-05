@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo VoxChart Windows Installer Builder v1.0.0
echo ========================================
echo.

REM Check Python
python --version | findstr /C:"3.1" >nul
if errorlevel 1 (
    echo ERROR: Python 3.10+ required. Download from python.org
    pause
    exit /b 1
)

REM Create venv if missing
if not exist venv (
    echo Creating virtual environment...
    py -m venv venv
)

REM Activate venv
call venv\Scripts\activate

REM Install/update requirements
echo Installing requirements...
pip install --upgrade pip setuptools wheel
pip install -r requirements-windows-frozen.txt --quiet

REM Test GPU + mic
echo.
echo Testing GPU and microphone...
call test_windows.bat

REM Build EXE
echo.
echo Building VoxChart.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name VoxChart ^
    --icon=VoxChart.ico ^
    --add-data "medical_terms.db;." ^
    --add-data "training_corpus;training_corpus" ^
    --hidden-import=torch ^
    --hidden-import=sounddevice ^
    --collect-all faster_whisper ^
    --collect-all customtkinter ^
    app.py

if errorlevel 1 (
    echo.
    echo Build failed. Check errors above.
    pause
    exit /b 1
)

REM Create installer
echo.
echo Creating installer...
powershell -Command "& {
    $installer = 'dist/VoxChart_Setup_v1.0.0.exe'
    $exe = 'dist/VoxChart.exe'
    if (Test-Path $exe) {
        Copy-Item $exe $installer
        Write-Host 'Installer created: dist/VoxChart_Setup_v1.0.0.exe' -Foreground Green
        Write-Host 'Double-click to install anywhere on Windows!' -Foreground Green
    }
}"

echo.
echo ========================================
echo BUILD COMPLETE!
echo.
echo Installer: dist\VoxChart_Setup_v1.0.0.exe
echo Test: Double-click it to install + run
echo.
echo To distribute: Copy just the .exe file (90MB)
echo ========================================
pause
