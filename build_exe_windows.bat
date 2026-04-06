@echo off
cd /d %~dp0
call venv\Scripts\activate

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building VoxChart EXE...
pyinstaller MedicalDictation.spec --clean --noconfirm

if not exist dist\VoxChart\VoxChart.exe (
    echo.
    echo Build FAILED. Check output above.
    pause & exit /b 1
)

echo.
echo =============================================
echo  Build SUCCESS!
echo  EXE: dist\VoxChart\VoxChart.exe
echo =============================================
echo.

rem -- Auto-sign if cert exists --
set CERT=signing\voxchart_cert.pfx
if exist %CERT% (
    echo Signing EXE...
    powershell -ExecutionPolicy Bypass -File "%~dp0sign_exe.ps1"
    if errorlevel 1 (
        echo WARNING: Signing failed. EXE is unsigned.
    ) else (
        echo EXE signed successfully.
    )
) else (
    echo.
    echo NOTE: No signing certificate found at %CERT%
    echo To sign the EXE ^(recommended^), run:
    echo   .\create_self_signed_cert.ps1     ^(free, self-signed^)
    echo   .\sign_exe.ps1 -PfxPath your.pfx  ^(commercial cert^)
)

echo.
pause
