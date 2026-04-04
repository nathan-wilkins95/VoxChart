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
echo Starting Medical Dictation App...
python app.py
if errorlevel 1 ( echo App exited with error. & pause )
