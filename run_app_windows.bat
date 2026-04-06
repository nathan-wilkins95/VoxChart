@echo off
cd /d %~dp0

if not exist venv (
    echo Virtual environment not found.
    echo Run this first:
    echo   py -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements-windows.txt
    pause & exit /b 1
)

call venv\Scripts\activate

rem -- Auto-create desktop shortcut on first run (silent) --
if not exist .shortcut_created (
    echo Creating desktop shortcut...
    python shortcut_utils.py
)

echo Starting VoxChart...
python app.py
if errorlevel 1 ( echo App exited with error. & pause )
