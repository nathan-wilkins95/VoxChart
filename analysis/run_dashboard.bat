@echo off
title VoxChart ROI Dashboard
color 1F

echo.
echo  ================================================
echo   Vox Medical -- ROI Dashboard Launcher
echo   Less charting. More caring.
echo  ================================================
echo.

:: Navigate to analysis folder (where this .bat lives)
cd /d "%~dp0"

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/3] Virtual environment found.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install / upgrade dependencies
echo [2/3] Installing dependencies...
pip install -q -r requirements.txt

:: Open browser after short delay
echo [3/3] Launching dashboard...
echo.
echo  Open your browser to: http://localhost:8050
echo  Press Ctrl+C in this window to stop the server.
echo.
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:8050"

:: Run the Dash app
python dashboard/app.py

echo.
echo  Dashboard stopped. Press any key to close.
pause >nul
