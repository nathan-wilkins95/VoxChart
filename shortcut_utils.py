"""
shortcut_utils.py

Cross-platform desktop shortcut creation for VoxChart.
Called by both run_app_windows.bat (via Python) and the in-app button.
"""

from __future__ import annotations
import os
import sys
import platform
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent
APP_NAME   = "VoxChart"
SHORTCUT_MARKER = REPO_ROOT / ".shortcut_created"


def _find_icon() -> str:
    """Return best available icon path as string."""
    candidates = [
        REPO_ROOT / "assets" / "voxchart.ico",
        REPO_ROOT / "assets" / "icon.ico",
        REPO_ROOT / "icon.ico",
        REPO_ROOT / "assets" / "voxchart.png",
        REPO_ROOT / "icon_preview.png",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ""


def create_windows_shortcut(silent: bool = False) -> tuple[bool, str]:
    """
    Create a Windows .lnk shortcut on the Desktop.
    Returns (success, message).
    """
    try:
        import winreg  # noqa: F401 - confirms we are on Windows
    except ImportError:
        return False, "Not running on Windows."

    try:
        import win32com.client  # type: ignore
        shell = win32com.client.Dispatch("WScript.Shell")
    except Exception:
        # Fallback: call PowerShell directly
        return _create_windows_shortcut_powershell(silent)

    try:
        desktop = Path(shell.SpecialFolders("Desktop"))
        lnk_path = desktop / f"{APP_NAME}.lnk"

        exe_path = REPO_ROOT / "dist" / "VoxChart" / "VoxChart.exe"
        bat_path = REPO_ROOT / "run_app_windows.bat"
        icon     = _find_icon()

        shortcut = shell.CreateShortCut(str(lnk_path))

        if exe_path.exists():
            shortcut.Targetpath       = str(exe_path)
            shortcut.WorkingDirectory = str(exe_path.parent)
        elif bat_path.exists():
            shortcut.Targetpath       = "cmd.exe"
            shortcut.Arguments        = f'/c "{bat_path}"'
            shortcut.WorkingDirectory = str(REPO_ROOT)
            shortcut.WindowStyle      = 7  # minimized - hides console flash
        else:
            return False, "Could not find VoxChart.exe or run_app_windows.bat."

        shortcut.Description = "VoxChart - Offline AI Medical Dictation"
        if icon:
            shortcut.IconLocation = f"{icon},0"
        shortcut.save()
        SHORTCUT_MARKER.touch()
        msg = f"Desktop shortcut created: {lnk_path}"
        if not silent:
            print(msg)
        return True, msg
    except Exception as e:
        return False, f"Shortcut creation failed: {e}"


def _create_windows_shortcut_powershell(silent: bool = False) -> tuple[bool, str]:
    """Fallback: call the existing .ps1 via PowerShell."""
    ps1 = REPO_ROOT / "create_desktop_shortcut.ps1"
    if not ps1.exists():
        return False, "create_desktop_shortcut.ps1 not found."
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            SHORTCUT_MARKER.touch()
            msg = "Desktop shortcut created via PowerShell."
            if not silent:
                print(msg)
            return True, msg
        else:
            return False, result.stderr.strip() or "PowerShell script failed."
    except Exception as e:
        return False, f"PowerShell fallback failed: {e}"


def create_linux_shortcut(silent: bool = False) -> tuple[bool, str]:
    """
    Create a .desktop file on Linux/Ubuntu Desktop and in
    ~/.local/share/applications (app menu).
    Returns (success, message).
    """
    try:
        desktop_dir = Path.home() / "Desktop"
        apps_dir    = Path.home() / ".local" / "share" / "applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        apps_dir.mkdir(parents=True, exist_ok=True)

        # Find Python interpreter (prefer venv)
        venv_python = ""
        for candidate in [
            REPO_ROOT / "venv" / "bin" / "python",
            REPO_ROOT / ".venv" / "bin" / "python",
            REPO_ROOT / "env" / "bin" / "python",
        ]:
            if candidate.exists():
                venv_python = str(candidate)
                break
        if not venv_python:
            venv_python = sys.executable

        binary = REPO_ROOT / "dist" / "VoxChart" / "VoxChart"
        if binary.exists():
            exec_line = str(binary)
        else:
            exec_line = f'bash -c \'cd "{REPO_ROOT}" && "{venv_python}" app.py\''

        icon = _find_icon() or "utilities-terminal"

        content = f"""[Desktop Entry]
Version=1.3
Type=Application
Name={APP_NAME}
Comment=Offline AI Medical Dictation - powered by Whisper
Exec={exec_line}
Icon={icon}
Path={REPO_ROOT}
Terminal=false
StartupNotify=true
Categories=AudioVideo;Audio;Medical;
Keywords=dictation;medical;voice;AI;chart;
"""
        shortcut_path = desktop_dir / "voxchart.desktop"
        apps_path     = apps_dir    / "voxchart.desktop"

        shortcut_path.write_text(content, encoding="utf-8")
        shortcut_path.chmod(0o755)
        apps_path.write_text(content, encoding="utf-8")
        apps_path.chmod(0o755)

        # Mark trusted in GNOME
        try:
            import subprocess
            subprocess.run(["gio", "set", str(shortcut_path),
                            "metadata::trusted", "true"],
                           capture_output=True, timeout=5)
            subprocess.run(["update-desktop-database", str(apps_dir)],
                           capture_output=True, timeout=5)
        except Exception:
            pass

        SHORTCUT_MARKER.touch()
        msg = f"Desktop shortcut created: {shortcut_path}"
        if not silent:
            print(msg)
        return True, msg
    except Exception as e:
        return False, f"Linux shortcut creation failed: {e}"


def create_shortcut(silent: bool = False) -> tuple[bool, str]:
    """Auto-detect OS and create the appropriate shortcut."""
    system = platform.system()
    if system == "Windows":
        return create_windows_shortcut(silent=silent)
    elif system == "Linux":
        return create_linux_shortcut(silent=silent)
    else:
        return False, f"Unsupported platform: {system}"


def shortcut_already_exists() -> bool:
    """Return True if shortcut has been created before (marker file exists)."""
    return SHORTCUT_MARKER.exists()


if __name__ == "__main__":
    ok, msg = create_shortcut(silent=False)
    print("OK:" if ok else "FAIL:", msg)
