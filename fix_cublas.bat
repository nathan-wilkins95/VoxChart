@echo off
rem CUDA 13.2 cuBLAS symlink for faster-whisper
cd /d "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"

if exist "v13.2\bin\cublas64_12.dll" (
    echo cuBLAS 12 already exists - good
    exit /b 0
)

if exist "v13.2\bin\cublas64_13.dll" (
    echo Creating cublas64_12.dll symlink from 13.2
    copy "v13.2\bin\cublas64_13.dll" "v13.2\bin\cublas64_12.dll"
    echo Fixed - reboot recommended
    exit /b 0
)

echo No cuBLAS found - CUDA install incomplete
dir v13.2\bin\cublas*
pause
