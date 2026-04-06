@echo off
setlocal
title VoxChart Build Menu

:menu
cls
echo ============================================
echo   VoxChart Build Menu
echo ============================================
echo.
echo   [1] Run app (dev mode)
echo   [2] Build EXE + sign
echo   [3] Sign existing EXE only
echo   [4] Run tests
echo   [5] Exit
echo.
set /p choice=Select option: 

if "%choice%"=="1" goto run_app
if "%choice%"=="2" goto build_exe
if "%choice%"=="3" goto sign_only
if "%choice%"=="4" goto run_tests
if "%choice%"=="5" goto end
goto menu

:run_app
cls
echo Starting VoxChart in dev mode...
call venv\Scripts\activate.bat 2>nul || echo WARNING: venv not found, using system Python
python app.py
goto menu

:build_exe
cls
echo Building EXE...
call venv\Scripts\activate.bat 2>nul
pip install packaging --quiet
pyinstaller MedicalDictation.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo BUILD FAILED. Check output above.
    pause
    goto menu
)
echo.
echo EXE built: dist\VoxChart\VoxChart.exe
echo.

REM Auto-sign if cert exists
if exist signing\voxchart_cert.pfx (
    echo Signing EXE...
    signtool sign /fd SHA256 /p12 signing\voxchart_cert.pfx /p "%SIGN_PASSWORD%" ^
        /t http://timestamp.digicert.com ^
        dist\VoxChart\VoxChart.exe
    if errorlevel 1 (
        echo WARNING: Signing failed. Set SIGN_PASSWORD env var.
    ) else (
        echo EXE signed successfully.
    )
) else (
    echo NOTE: No signing cert found at signing\voxchart_cert.pfx
    echo       EXE is unsigned. SmartScreen will warn on first run.
)
pause
goto menu

:sign_only
cls
if not exist dist\VoxChart\VoxChart.exe (
    echo ERROR: dist\VoxChart\VoxChart.exe not found. Build first.
    pause
    goto menu
)
if not exist signing\voxchart_cert.pfx (
    echo ERROR: signing\voxchart_cert.pfx not found.
    pause
    goto menu
)
signtool sign /fd SHA256 /p12 signing\voxchart_cert.pfx /p "%SIGN_PASSWORD%" ^
    /t http://timestamp.digicert.com ^
    dist\VoxChart\VoxChart.exe
if errorlevel 1 echo FAILED. Set SIGN_PASSWORD env var and try again.
if not errorlevel 1 echo Signed successfully.
pause
goto menu

:run_tests
cls
call venv\Scripts\activate.bat 2>nul
python -m pytest tests\ -v 2>nul || python test_windows.bat
pause
goto menu

:end
endlocal
