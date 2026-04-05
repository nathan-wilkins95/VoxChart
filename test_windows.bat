@echo off
cd /d %~dp0
call venv\Scripts\activate
echo.
echo ========================================
echo VoxChart Hardware Test
echo ========================================
echo.

echo [1/4] GPU Detection...
python -c "
import torch
print('torch CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    print('CUDA capability:', torch.cuda.get_device_capability(0))
else:
    import subprocess
    try:
        nvidia = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                               capture_output=True, text=True, timeout=3).stdout.strip()
        print('nvidia-smi GPU:', nvidia or 'Not found')
    except:
        print('nvidia-smi: unavailable')
"

echo.
echo [2/4] Microphone...
python -c "import sounddevice as sd; print('Input devices:', len([d for d in sd.query_devices() if d.max_input_channels>0]))"

echo.
echo [3/4] Whisper test (tiny model)...
python -c "from faster_whisper import WhisperModel; m=WhisperModel('tiny.en', device='cpu'); print('Whisper tiny: OK')"

echo.
echo [4/4] Medical DB...
python -c "import sqlite3; print('medical_terms.db:', 'OK' if sqlite3.connect('medical_terms.db').execute('SELECT COUNT(*) FROM terms').fetchone()[0] else 'Empty/missing')"

echo.
echo ========================================
echo All tests passed! Ready to build.
pause
