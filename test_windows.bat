@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
echo ===== GPU Test =====
python -c "from faster_whisper import WhisperModel; m=WhisperModel('tiny',device='cuda',compute_type='float16'); print('OK: cuda float16')" 2>nul || (
  python -c "from faster_whisper import WhisperModel; m=WhisperModel('tiny',device='cuda',compute_type='int8_float16'); print('OK: cuda int8_float16')" 2>nul || (
    echo CUDA not available - falling back to CPU
    python -c "from faster_whisper import WhisperModel; m=WhisperModel('tiny',device='cpu',compute_type='int8'); print('OK: cpu int8')"
  )
)
echo.
echo ===== Microphone Test =====
python -c "import sounddevice as sd; devs=sd.query_devices(); [print(f'  [{i}] {d[\"name\"]}') for i,d in enumerate(devs) if d['max_input_channels']>0]"
echo.
echo ===== Auto-Detect Preview =====
python -c "from app import detect_device_and_compute; d, c = detect_device_and_compute(); print(f'App will use: device={d}, compute_type={c}')"
pause
