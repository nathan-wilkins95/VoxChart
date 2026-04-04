@echo off
cd /d %~dp0
call venv\Scripts\activate

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Building EXE...
pyinstaller MedicalDictation.spec --clean --noconfirm

if exist dist\MedicalDictation\MedicalDictation.exe (
    echo.
    echo =============================================
    echo  Build SUCCESS!
    echo  EXE: dist\MedicalDictation\MedicalDictation.exe
    echo =============================================
) else (
    echo.
    echo Build FAILED. Check output above.
)
pause
