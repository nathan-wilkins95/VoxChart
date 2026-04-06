"""
crash_reporter.py

VoxChart crash and bug reporting system.

Features:
  - Rotating log file  (logs/voxchart.log, max 1MB x 3 backups)
  - Global sys.excepthook  catches ALL unhandled exceptions
  - CrashDialog  shown to user on crash with full traceback
  - copy-to-clipboard  for easy manual paste into GitHub
  - 'Open GitHub Issues'  button  - prefills a new issue URL
  - Manual 'Report Bug' dialog  (no crash required)
  - System info automatically included (OS, Python, GPU, config)
"""

from __future__ import annotations
import sys
import os
import platform
import traceback
import logging
import webbrowser
import urllib.parse
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

REPO_ROOT   = Path(__file__).resolve().parent
LOG_DIR     = REPO_ROOT / "logs"
LOG_FILE    = LOG_DIR / "voxchart.log"
GITHUB_REPO = "nathan-wilkins95/VoxChart"
GITHUB_ISSUES_URL = f"https://github.com/{GITHUB_REPO}/issues/new"

# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """Configure root logger with rotating file + stderr stream."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    return root


logger = logging.getLogger("voxchart")


# ── System info ───────────────────────────────────────────────────────────────

def get_system_info() -> str:
    lines = [
        f"VoxChart crash report",
        f"Time      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"OS        : {platform.system()} {platform.release()} ({platform.version()})",
        f"Machine   : {platform.machine()}",
        f"Python    : {sys.version}",
    ]
    # GPU info
    try:
        import torch
        if torch.cuda.is_available():
            lines.append(f"GPU       : {torch.cuda.get_device_name(0)} (CUDA {torch.version.cuda})")
        else:
            lines.append("GPU       : None / CPU mode")
    except Exception:
        lines.append("GPU       : torch not available")
    # Config
    try:
        import json
        cfg_path = REPO_ROOT / "voxchart_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            lines.append(f"Device    : {cfg.get('device', 'unknown')}")
            lines.append(f"Mic index : {cfg.get('mic_index', 'unknown')}")
            lines.append(f"Mic name  : {cfg.get('mic_name', 'unknown')}")
    except Exception:
        pass
    # Log file location
    lines.append(f"Log file  : {LOG_FILE}")
    return "\n".join(lines)


# ── Format full crash report ──────────────────────────────────────────────────

def format_crash_report(exc_type, exc_value, exc_tb) -> str:
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sysinfo = get_system_info()
    return (
        f"{sysinfo}\n"
        f"\n{'=' * 60}\n"
        f"TRACEBACK\n"
        f"{'=' * 60}\n"
        f"{tb_str}"
    )


# ── GitHub issue URL builder ──────────────────────────────────────────────────

def build_github_issue_url(title: str, body: str) -> str:
    params = urllib.parse.urlencode({
        "title": title,
        "body": body,
        "labels": "bug",
    })
    return f"{GITHUB_ISSUES_URL}?{params}"


def open_github_issue(report: str, title: str = "Bug Report") -> None:
    # GitHub URL max is ~8192 chars; truncate body if needed
    body = f"```\n{report[:6000]}\n```\n\n**Additional context:** (describe what you were doing)"
    url = build_github_issue_url(title, body)
    webbrowser.open(url)


# ── Crash Dialog (shown to user on unhandled exception) ───────────────────────

class CrashDialog:
    """
    Modal Tkinter dialog shown when the app crashes.
    Safe to call from sys.excepthook (no CustomTkinter dependency).
    """

    def __init__(self, report: str):
        self.report = report
        self._run()

    def _run(self):
        try:
            import tkinter as tk
            from tkinter import scrolledtext

            root = tk.Tk()
            root.title("VoxChart - Unexpected Error")
            root.geometry("700x520")
            root.resizable(True, True)
            try:
                root.configure(bg="#1a1a2e")
            except Exception:
                pass

            BG   = "#1a1a2e"
            FG   = "#e0e0e0"
            RED  = "#d93025"
            BLUE = "#2b7cff"
            GRAY = "#555"

            tk.Label(
                root,
                text="VoxChart encountered an unexpected error",
                font=("Segoe UI", 14, "bold"),
                bg=BG, fg=RED,
            ).pack(pady=(18, 4))

            tk.Label(
                root,
                text="The crash has been saved to logs/voxchart.log  -  please report it so we can fix it.",
                font=("Segoe UI", 10),
                bg=BG, fg=FG,
            ).pack(pady=(0, 10))

            txt = scrolledtext.ScrolledText(
                root, width=85, height=16,
                font=("Courier New", 9),
                bg="#0d0d1a", fg="#c8c8c8",
                relief="flat", padx=8, pady=8,
            )
            txt.pack(fill="both", expand=True, padx=16, pady=(0, 10))
            txt.insert("1.0", self.report)
            txt.config(state="disabled")

            btn_frame = tk.Frame(root, bg=BG)
            btn_frame.pack(fill="x", padx=16, pady=(0, 16))

            def copy_report():
                root.clipboard_clear()
                root.clipboard_append(self.report)
                copy_btn.config(text="Copied!")
                root.after(2000, lambda: copy_btn.config(text="Copy Report"))

            def open_issue():
                exc_lines = [l for l in self.report.splitlines() if "Error" in l or "Exception" in l]
                title = exc_lines[0].strip()[:80] if exc_lines else "VoxChart crash report"
                open_github_issue(self.report, title=title)

            tk.Button(
                btn_frame, text="Copy Report", command=copy_report,
                bg=GRAY, fg=FG, relief="flat", padx=14, pady=6, cursor="hand2",
            ).pack(side="left", padx=(0, 8))

            copy_btn = btn_frame.winfo_children()[-1]  # ref for text reset

            tk.Button(
                btn_frame, text="Open GitHub Issue", command=open_issue,
                bg=BLUE, fg="white", relief="flat", padx=14, pady=6, cursor="hand2",
            ).pack(side="left", padx=(0, 8))

            tk.Button(
                btn_frame, text="Open Log Folder",
                command=lambda: _open_folder(LOG_DIR),
                bg=GRAY, fg=FG, relief="flat", padx=14, pady=6, cursor="hand2",
            ).pack(side="left")

            tk.Button(
                btn_frame, text="Close", command=root.destroy,
                bg=RED, fg="white", relief="flat", padx=14, pady=6, cursor="hand2",
            ).pack(side="right")

            root.mainloop()
        except Exception:
            # Last-resort: if tkinter itself fails, just print
            print(self.report, file=sys.stderr)


def _open_folder(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == "Windows":
        os.startfile(str(path))
    elif system == "Darwin":
        import subprocess; subprocess.Popen(["open", str(path)])
    else:
        import subprocess; subprocess.Popen(["xdg-open", str(path)])


# ── Global exception hook ─────────────────────────────────────────────────────

def install_exception_hook():
    """
    Install sys.excepthook so any unhandled exception:
      1. Logs the crash to logs/voxchart.log
      2. Shows the CrashDialog to the user
    """
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        report = format_crash_report(exc_type, exc_value, exc_tb)
        logger.critical("UNHANDLED EXCEPTION:\n%s", report)
        CrashDialog(report)

    sys.excepthook = _hook


# ── Manual bug report dialog (no crash needed) ────────────────────────────────

class BugReportDialog:
    """
    In-app 'Report Bug' dialog.
    Uses CustomTkinter if available, falls back to plain Tkinter.
    """

    def __init__(self, parent=None):
        self.parent = parent
        self._run()

    def _run(self):
        try:
            import customtkinter as ctk
            self._run_ctk(ctk)
        except ImportError:
            self._run_tk()

    def _run_ctk(self, ctk):
        win = ctk.CTkToplevel(self.parent)
        win.title("Report a Bug")
        win.geometry("620x560")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="Report a Bug",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(win,
                     text="Describe what happened. System info is attached automatically.",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 10))

        ctk.CTkLabel(win, text="What were you doing when the issue occurred?",
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", padx=24)
        desc_box = ctk.CTkTextbox(win, height=100, font=ctk.CTkFont(family="Segoe UI", size=12))
        desc_box.pack(fill="x", padx=24, pady=(4, 12))
        desc_box.insert("1.0", "e.g., App froze when I clicked Start Dictation with GPU mode")

        ctk.CTkLabel(win, text="Steps to reproduce (optional):",
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", padx=24)
        steps_box = ctk.CTkTextbox(win, height=80, font=ctk.CTkFont(family="Segoe UI", size=12))
        steps_box.pack(fill="x", padx=24, pady=(4, 12))

        # Collapsible system info preview
        ctk.CTkLabel(win, text="System info (auto-included):",
                     font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(fill="x", padx=24)
        sysinfo_box = ctk.CTkTextbox(win, height=80, font=ctk.CTkFont(family="Courier New", size=10),
                                      text_color="gray")
        sysinfo_box.pack(fill="x", padx=24, pady=(2, 14))
        sysinfo_box.insert("1.0", get_system_info())
        sysinfo_box.configure(state="disabled")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        def _submit_github():
            desc  = desc_box.get("1.0", "end-1c").strip()
            steps = steps_box.get("1.0", "end-1c").strip()
            sysinfo = get_system_info()
            body = (
                f"## Description\n{desc}\n\n"
                f"## Steps to Reproduce\n{steps or 'N/A'}\n\n"
                f"## System Info\n```\n{sysinfo}\n```\n\n"
                f"## Log\nSee attached log or paste from `logs/voxchart.log`"
            )
            title = desc[:72] if desc else "Bug report from VoxChart"
            open_github_issue(body, title=title)
            win.grab_release()
            win.destroy()

        def _copy_report():
            desc    = desc_box.get("1.0", "end-1c").strip()
            sysinfo = get_system_info()
            report  = f"Bug Report\n{sysinfo}\n\nDescription:\n{desc}"
            win.clipboard_clear()
            win.clipboard_append(report)
            copy_btn.configure(text="Copied!")
            win.after(2000, lambda: copy_btn.configure(text="Copy to Clipboard"))

        def _open_log():
            _open_folder(LOG_DIR)

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", width=90,
                      command=lambda: (win.grab_release(), win.destroy())).pack(side="left")
        copy_btn = ctk.CTkButton(btn_frame, text="Copy to Clipboard", width=140,
                                  fg_color="#444", command=_copy_report)
        copy_btn.pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Open Log Folder", width=130,
                      fg_color="#444", command=_open_log).pack(side="left")
        ctk.CTkButton(btn_frame, text="Submit on GitHub", width=150,
                      fg_color="#2b7cff", hover_color="#1a5acc",
                      command=_submit_github).pack(side="right")

    def _run_tk(self):
        import tkinter as tk
        from tkinter import scrolledtext
        win = tk.Toplevel(self.parent)
        win.title("Report a Bug")
        win.geometry("580x400")
        tk.Label(win, text="Describe the bug:").pack(anchor="w", padx=10, pady=(10, 0))
        txt = scrolledtext.ScrolledText(win, height=8)
        txt.pack(fill="both", expand=True, padx=10, pady=6)
        def submit():
            desc = txt.get("1.0", "end-1c").strip()
            open_github_issue(get_system_info() + "\n\n" + desc, title=desc[:72] or "Bug report")
            win.destroy()
        tk.Button(win, text="Submit on GitHub", command=submit).pack(pady=10)


# ── Convenience: log recent crash from log file ───────────────────────────────

def get_recent_log(lines: int = 60) -> str:
    """Return the last N lines of the log file."""
    if not LOG_FILE.exists():
        return "No log file found yet."
    try:
        text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        return "\n".join(all_lines[-lines:])
    except Exception as e:
        return f"Could not read log: {e}"
