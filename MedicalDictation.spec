# -*- mode: python ; coding: utf-8 -*-
# VoxChart PyInstaller spec
# Auto-signs after build if signing\voxchart_cert.pfx exists.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect faster-whisper model data and ctranslate2 binaries
whisper_datas  = collect_data_files("faster_whisper")
ctranslate_datas = collect_data_files("ctranslate2")

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets',            'assets'),
        ('voxchart_config.json', '.'),
        *whisper_datas,
        *ctranslate_datas,
    ],
    hiddenimports=[
        # App modules
        'dictation_engine',
        'epic_exporter',
        'medical_postprocessor',
        'shortcut_utils',
        'crash_reporter',
        'session_history',
        'templates',
        'updater',
        'build_medical_db',
        # ML / audio
        'faster_whisper',
        'ctranslate2',
        'sounddevice',
        'soundfile',
        'numpy',
        'torch',
        'packaging',
        'packaging.version',
        # UI
        'customtkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        # stdlib used at runtime
        'sqlite3',
        'json',
        'logging',
        'logging.handlers',
        'threading',
        'urllib.request',
        'urllib.parse',
        'webbrowser',
        'pathlib',
        'platform',
        'subprocess',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pandas', 'scipy', 'IPython', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoxChart',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                        # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
    icon=['assets\\VoxChart.ico'],        # <-- fixed path
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VoxChart',
)
