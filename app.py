import os
import sys
import json
import math
import platform
import subprocess
import threading
import webbrowser
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from dictation_engine import DictationEngine
from epic_exporter import format_for_epic, copy_to_clipboard, export_to_file
from shortcut_utils import create_shortcut, shortcut_already_exists
from crash_reporter import setup_logging, install_exception_hook, BugReportDialog, get_recent_log, LOG_DIR, _open_folder
from session_history import (init_db, start_session, stop_session,
                              list_sessions, delete_session, read_transcript,
                              search_sessions)
from templates import all_templates, get_template, add_custom_template
from updater import check_for_update
from settings import SettingsWindow, load_config, save_config
from autosave import AutoSaver, check_for_crash_recovery
from version import APP_VERSION
from about_dialog import AboutDialog
from splash import SplashScreen

# -- Bootstrap --
setup_logging()
install_exception_hook()

import logging
logger = logging.getLogger("voxchart.app")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

OUTPUT_DIR          = "chart_notes"
DEFAULT_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "chart_note.txt")


def detect_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
    except Exception:
        pass
    return False, None


# ---------------------------------------------------------------------------
#  Onboarding Wizard
# ---------------------------------------------------------------------------

class OnboardingWizard(ctk.CTkToplevel):
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.title("VoxChart Setup")
        self.geometry("560x480")
        self.resizable(False, False)
        self.grab_set()
        self.on_complete = on_complete
        self.step = 0
        self.gpu_available, self.gpu_name = detect_gpu()
        self.chosen_device   = ctk.StringVar(value="cuda" if self.gpu_available else "cpu")
        self.wizard_mic_var  = ctk.StringVar()
        self.frames = []
        self._build_steps()
        self._show_step(0)

    def _build_steps(self):
        self.frames = [self._build_welcome(), self._build_device_step(), self._build_mic_step()]

    def _build_welcome(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Welcome to VoxChart",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(40, 10))
        ctk.CTkLabel(f, text=(
            "VoxChart turns your voice into structured medical chart notes\n"
            "using a fully offline AI — no internet required after setup.\n\n"
            "This wizard will configure your microphone and compute device."
        ), font=ctk.CTkFont(size=13), justify="center").pack(pady=10, padx=30)
        self._nav_buttons(f, back=False)
        return f

    def _build_device_step(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Step 1 of 2 — Compute Device",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(30, 10))
        gpu_label = f"GPU detected: {self.gpu_name}" if self.gpu_available else "No NVIDIA GPU detected"
        gpu_color = "green" if self.gpu_available else "orange"
        rec_text  = "GPU recommended — faster transcription." if self.gpu_available else "CPU mode. Transcription may be slower."
        ctk.CTkLabel(f, text=gpu_label, font=ctk.CTkFont(size=13, weight="bold"), text_color=gpu_color).pack(pady=(10, 4))
        ctk.CTkLabel(f, text=rec_text,  font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 20))
        ctk.CTkLabel(f, text="Select compute device:", font=ctk.CTkFont(size=13)).pack()
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(pady=10)
        ctk.CTkRadioButton(row, text="GPU (CUDA)", variable=self.chosen_device, value="cuda",
                           state="normal" if self.gpu_available else "disabled").pack(anchor="w", padx=20, pady=6)
        ctk.CTkRadioButton(row, text="CPU", variable=self.chosen_device, value="cpu").pack(anchor="w", padx=20, pady=6)
        if not self.gpu_available:
            self.chosen_device.set("cpu")
        self._nav_buttons(f)
        return f

    def _build_mic_step(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Step 2 of 2 — Microphone",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(30, 10))
        self.wizard_mic_menu = ctk.CTkOptionMenu(f, variable=self.wizard_mic_var, width=380)
        self.wizard_mic_menu.pack(pady=6)
        self.wizard_level_label = ctk.CTkLabel(f, text="Level: --",
                                                font=ctk.CTkFont(size=12), text_color="gray")
        self.wizard_level_label.pack(pady=4)
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(pady=6)
        ctk.CTkButton(row, text="Refresh", command=self._refresh_wizard_mics, width=90).pack(side="left", padx=6)
        self._refresh_wizard_mics()
        self._nav_buttons(f, next_text="Finish")
        return f

    def _refresh_wizard_mics(self):
        try:
            import sounddevice as sd
            opts = [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices())
                    if d["max_input_channels"] > 0]
            self.wizard_mic_menu.configure(values=opts or ["No microphones found"])
            self.wizard_mic_var.set(opts[0] if opts else "No microphones found")
        except Exception as e:
            self.wizard_mic_menu.configure(values=[f"Error: {e}"])

    def _nav_buttons(self, parent, back=True, next_text="Next"):
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(side="bottom", fill="x", padx=20, pady=20)
        if back:
            ctk.CTkButton(nav, text="Back", width=100, fg_color="gray",
                          command=lambda: self._show_step(self.step - 1)).pack(side="left")
        ctk.CTkButton(nav, text=next_text, width=120, command=self._next_or_finish).pack(side="right")

    def _show_step(self, idx):
        for f in self.frames:
            f.pack_forget()
        self.step = idx
        self.frames[idx].pack(fill="both", expand=True)

    def _next_or_finish(self):
        if self.step < len(self.frames) - 1:
            self._show_step(self.step + 1)
        else:
            self._finish()

    def _finish(self):
        mic_str = self.wizard_mic_var.get()
        try:
            mic_idx  = int(mic_str.split(":")[0])
            mic_name = mic_str.split(":", 1)[1].strip()
        except Exception:
            mic_idx, mic_name = 0, mic_str
        cfg = load_config()
        cfg.update({
            "first_run_complete": True,
            "device":       self.chosen_device.get(),
            "compute_type": "float16" if self.chosen_device.get() == "cuda" else "int8",
            "mic_index":    mic_idx,
            "mic_name":     mic_name,
        })
        save_config(cfg)
        self.grab_release()
        self.destroy()
        self.on_complete(cfg)


# ---------------------------------------------------------------------------
#  Fine-tune Dialog
# ---------------------------------------------------------------------------

class FineTuneDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Fine-tune Whisper on Your Voice")
        self.geometry("500x400")
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Voice Fine-Tuning",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(self,
            text="Fine-tunes Whisper on your recorded sessions.\n"
                 "Requires: pip install transformers datasets accelerate",
            font=ctk.CTkFont(size=12), text_color="gray", justify="center").pack(pady=(0, 10))
        self._log = ctk.CTkTextbox(self, height=200,
                                   font=ctk.CTkFont(family="Courier New", size=10),
                                   state="disabled")
        self._log.pack(fill="both", expand=True, padx=16, pady=4)
        self._btn = ctk.CTkButton(self, text="Start Fine-tuning", command=self._start)
        self._btn.pack(pady=10)
        ctk.CTkButton(self, text="Close", fg_color="gray", width=100,
                      command=lambda: (self.grab_release(), self.destroy())).pack(pady=(0, 14))

    def _log_msg(self, msg: str):
        self.after(0, lambda m=msg: self._append(m))

    def _append(self, msg: str):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _start(self):
        self._btn.configure(state="disabled", text="Training...")
        from training_corpus import fine_tune
        def run():
            try:
                fine_tune(on_progress=self._log_msg)
                self._log_msg("\n\u2705 Fine-tuning complete! Restart the app to use your model.")
            except Exception as e:
                self._log_msg(f"\n\u274c Error: {e}")
            finally:
                self.after(0, lambda: self._btn.configure(state="normal", text="Start Fine-tuning"))
        threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------------------
#  Epic Export Dialog
# ---------------------------------------------------------------------------

class EpicExportDialog(ctk.CTkToplevel):
    def __init__(self, parent, transcript: str):
        super().__init__(parent)
        self.title("Copy to Epic")
        self.geometry("480x380")
        self.resizable(False, False)
        self.grab_set()
        self.transcript = transcript
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Epic Export",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Optional: fill in patient info for the note header.",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 14))
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=30, pady=4)
        fields = [("Provider Name", "e.g., Dr. Smith"), ("Patient Name", "e.g., John Doe"),
                  ("Date of Birth", "e.g., 01/15/1970"), ("MRN", "e.g., 123456")]
        self._entries: dict[str, ctk.CTkEntry] = {}
        for row, (label, ph) in enumerate(fields):
            ctk.CTkLabel(form, text=label, width=130, anchor="w").grid(row=row, column=0, padx=(0, 10), pady=6, sticky="w")
            e = ctk.CTkEntry(form, width=260, placeholder_text=ph)
            e.grid(row=row, column=1, pady=6)
            self._entries[label] = e
        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(fill="x", padx=30, pady=20)
        ctk.CTkButton(btn, text="Cancel", fg_color="gray", width=100, command=self.destroy).pack(side="left")
        ctk.CTkButton(btn, text="Copy to Epic Clipboard", width=220, command=self._export).pack(side="right")

    def _export(self):
        fmt  = format_for_epic(self.transcript,
                               provider_name=self._entries["Provider Name"].get().strip(),
                               patient_name=self._entries["Patient Name"].get().strip(),
                               dob=self._entries["Date of Birth"].get().strip(),
                               mrn=self._entries["MRN"].get().strip())
        saved = export_to_file(fmt)
        copy_to_clipboard(fmt)
        self.grab_release()
        self.destroy()
        messagebox.showinfo("Copied!",
            f"Epic note copied to clipboard!\n\n1. Open Epic\n2. Open your note\n3. Ctrl+V\n\nSaved to:\n{saved}")


# ---------------------------------------------------------------------------
#  Update Banner Dialog (with release notes)
# ---------------------------------------------------------------------------

class UpdateNotesDialog(ctk.CTkToplevel):
    """Shows the full release notes when user clicks 'What's New'."""
    def __init__(self, parent, version: str, notes: str, url: str):
        super().__init__(parent)
        self.title(f"What's New in VoxChart {version}")
        self.geometry("540x420")
        self.grab_set()
        ctk.CTkLabel(self, text=f"VoxChart {version}",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#2b7cff").pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Release Notes",
                     font=ctk.CTkFont(size=12), text_color="#888").pack(pady=(0, 10))
        box = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier New", size=11))
        box.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        box.insert("1.0", notes or "No release notes available.")
        box.configure(state="disabled")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(row, text="Open on GitHub", width=150,
                      command=lambda: webbrowser.open(url)).pack(side="left")
        ctk.CTkButton(row, text="Close", fg_color="gray", width=100,
                      command=lambda: (self.grab_release(), self.destroy())
                      ).pack(side="right")


# ---------------------------------------------------------------------------
#  View Log Dialog
# ---------------------------------------------------------------------------

class ViewLogDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("VoxChart Log")
        self.geometry("800x500")
        self.grab_set()
        ctk.CTkLabel(self, text="Recent Log (last 60 lines)",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 4))
        self._box = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier New", size=10))
        self._box.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self._refresh()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(row, text="Refresh", command=self._refresh).pack(side="left")
        ctk.CTkButton(row, text="Open Log Folder",
                      command=lambda: _open_folder(LOG_DIR)).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Close", fg_color="gray",
                      command=lambda: (self.grab_release(), self.destroy())).pack(side="right")

    def _refresh(self):
        self._box.configure(state="normal")
        self._box.delete("1.0", "end")
        self._box.insert("1.0", get_recent_log(60))
        self._box.configure(state="disabled")


# ---------------------------------------------------------------------------
#  Save Template Dialog
# ---------------------------------------------------------------------------

class SaveTemplateDialog(ctk.CTkToplevel):
    def __init__(self, parent, body: str):
        super().__init__(parent)
        self.title("Save Custom Template")
        self.geometry("400x200")
        self.resizable(False, False)
        self.grab_set()
        ctk.CTkLabel(self, text="Template Name:",
                     font=ctk.CTkFont(size=14)).pack(pady=(24, 6))
        self._entry = ctk.CTkEntry(self, width=320, placeholder_text="e.g., My Cardiology Note")
        self._entry.pack(pady=6)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=16)
        ctk.CTkButton(row, text="Cancel", fg_color="gray", width=100,
                      command=lambda: (self.grab_release(), self.destroy())).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Save", width=100,
                      command=lambda: self._save(body)).pack(side="right", padx=8)

    def _save(self, body):
        name = self._entry.get().strip()
        if not name:
            messagebox.showwarning("Name required", "Please enter a template name.")
            return
        add_custom_template(name, body)
        messagebox.showinfo("Saved", f"Template '{name}' saved!")
        self.grab_release()
        self.destroy()


# ---------------------------------------------------------------------------
#  Main App
# ---------------------------------------------------------------------------

class MedicalDictationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"VoxChart v{APP_VERSION}")
        self.geometry("1100x740")
        self.output_file     = DEFAULT_OUTPUT_FILE
        self.is_recording    = False
        self.engine          = None
        self._session_id     = None
        self._waveform_job   = None
        self._update_banner  = None
        self._autosaver      = None
        self._splash         = None
        self._terms_window   = None  # strong reference to prevent GC
        init_db()
        logger.info("VoxChart %s starting", APP_VERSION)

        # Crash recovery check
        recovered = check_for_crash_recovery()
        if recovered:
            self.after(800, lambda p=recovered: self._offer_recovery(p))

        cfg = load_config()
        if not cfg.get("first_run_complete"):
            self.withdraw()
            self.after(200, self._run_wizard)
        else:
            self._show_splash(cfg)

    def _show_splash(self, cfg):
        self.withdraw()
        self._splash = SplashScreen(self, version=APP_VERSION)
        self._splash.set_status("Loading configuration...")
        self._splash.set_progress(0.1)
        def load_in_bg():
            try:
                self._splash.set_status("Initializing engine...")
                self._splash.set_progress(0.3)
                self._init_engine(cfg)
                self._splash.set_status("Building UI...")
                self._splash.set_progress(0.7)
                self.after(0, lambda: self._finish_launch(cfg))
            except Exception as e:
                logger.exception("Splash load failed")
                self.after(0, lambda: self._finish_launch(cfg))
        threading.Thread(target=load_in_bg, daemon=True).start()

    def _finish_launch(self, cfg):
        self._splash.set_progress(1.0)
        self._splash.set_status("Ready!")
        self.after(400, lambda: (
            self._splash.close(),
            self.deiconify(),
            self.build_ui(),
            self._bind_shortcuts(),
            self._post_launch()
        ))

    def _offer_recovery(self, path: str):
        if messagebox.askyesno("Recover Autosave",
                               f"VoxChart didn't shut down cleanly.\n"
                               f"Recover the last autosave?\n\n{path}"):
            try:
                text = Path(path).read_text(encoding="utf-8")
                self.transcript_text.delete("1.0", "end")
                self.transcript_text.insert("1.0", text)
                self.update_status("Autosave recovered.")
            except Exception as e:
                messagebox.showerror("Recovery failed", str(e))

    def _post_launch(self):
        if not shortcut_already_exists():
            self.after(1500, self._auto_create_shortcut)
        check_for_update(
            APP_VERSION,
            on_update_available=self._show_update_banner
        )

    def _auto_create_shortcut(self):
        ok, _ = create_shortcut(silent=True)
        if ok:
            self.update_status("Desktop shortcut created.")

    def _show_update_banner(self, version: str, url: str, notes: str = ""):
        self.after(0, lambda: self._build_update_banner(version, url, notes))

    def _build_update_banner(self, version: str, url: str, notes: str = ""):
        if self._update_banner:
            return
        banner = ctk.CTkFrame(self, fg_color="#1a4a1a", corner_radius=0)
        banner.pack(fill="x", before=self.winfo_children()[0])
        ctk.CTkLabel(banner,
                     text=f"  \u2b06  VoxChart {version} is available!",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#90ee90").pack(side="left", padx=10, pady=8)
        ctk.CTkButton(banner, text="What's New", width=110,
                      fg_color="#2d7a2d", hover_color="#3a9e3a",
                      command=lambda: UpdateNotesDialog(self, version, notes, url)
                      ).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(banner, text="Download", width=100,
                      fg_color="#2d7a2d", hover_color="#3a9e3a",
                      command=lambda: webbrowser.open(url)).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(banner, text="Dismiss", width=80, fg_color="gray",
                      command=lambda: (banner.destroy(),
                                       setattr(self, '_update_banner', None))
                      ).pack(side="right", padx=10, pady=8)
        self._update_banner = banner

    def _bind_shortcuts(self):
        self.bind("<Control-space>", lambda e: self.toggle_dictation())
        self.bind("<Control-s>",     lambda e: self.save_as())
        self.bind("<Control-o>",     lambda e: self.open_output_folder())
        self.bind("<Control-e>",     lambda e: self.copy_to_epic())
        self.bind("<Escape>",        lambda e: self._clear_transcript())
        self.bind("<F1>",            lambda e: self._show_shortcuts_help())
        self.bind("<F5>",            lambda e: self.refresh_mics())

    def _clear_transcript(self):
        if not self.is_recording:
            self.transcript_text.delete("1.0", "end")
            self.update_status("Transcript cleared.")

    def _show_shortcuts_help(self):
        messagebox.showinfo("Keyboard Shortcuts",
            "Ctrl+Space  Start / Stop\nCtrl+S  Save As\n"
            "Ctrl+E  Copy to Epic\nCtrl+O  Open Folder\n"
            "Esc  Clear Transcript\nF1  This Help\nF5  Refresh Mics")

    def _run_wizard(self):
        OnboardingWizard(self, on_complete=self._wizard_done)

    def _wizard_done(self, cfg):
        self._show_splash(cfg)

    def _init_engine(self, cfg):
        self.engine = DictationEngine(
            model_size=cfg.get("model_size", "large-v3-turbo"),
            device=cfg.get("device", "cpu"),
            compute_type=cfg.get("compute_type", "int8"),
            output_dir=OUTPUT_DIR,
            corpus_dir="training_corpus",
            language=cfg.get("language", "en"),
            mic_index=cfg.get("mic_index", None),
        )
        self.engine.on_text_callback   = self.append_transcript
        self.engine.on_status_callback = self.update_status
        self._cfg = cfg

    # -----------------------------------------------------------------------
    #  UI
    # -----------------------------------------------------------------------

    def build_ui(self):
        cfg       = self._cfg
        dev_label = "GPU (CUDA)" if cfg.get("device") == "cuda" else "CPU"
        mic_name  = cfg.get("mic_name", "Default")
        font_size = cfg.get("font_size", 13)

        top = ctk.CTkFrame(self, corner_radius=0)
        top.pack(fill="x", padx=10, pady=(10, 0))

        self.status_label = ctk.CTkLabel(
            top, text=f"Status: Ready  |  {dev_label}  |  Mic: {mic_name}  |  v{APP_VERSION}  |  F1=Help",
            justify="left")
        self.status_label.pack(side="left", padx=10, pady=10)

        # Top-right buttons
        ctk.CTkButton(top, text="Re-run Setup",  command=self._rerun_wizard,
                      width=110, fg_color="gray").pack(side="right", padx=10, pady=10)
        ctk.CTkButton(top, text="Pin to Desktop", command=self.create_shortcut_manual,
                      width=120, fg_color="#444").pack(side="right", padx=(0,6), pady=10)
        ctk.CTkButton(top, text="Report Bug",    command=self.open_bug_report,
                      width=110, fg_color="#7a1a1a", hover_color="#b02020"
                      ).pack(side="right", padx=(0,6), pady=10)
        ctk.CTkButton(top, text="View Log",      command=self.open_view_log,
                      width=90,  fg_color="#333").pack(side="right", padx=(0,6), pady=10)
        ctk.CTkButton(top, text="\u2139 About",  command=self.open_about,
                      width=80,  fg_color="#333").pack(side="right", padx=(0,6), pady=10)
        ctk.CTkButton(top, text="\u2699 Settings", command=self.open_settings,
                      width=100, fg_color="#2b4a7c", hover_color="#3a6aae"
                      ).pack(side="right", padx=(0,6), pady=10)
        ctk.CTkButton(top, text="\U0001f3a4 Fine-tune", command=self.open_finetune,
                      width=110, fg_color="#2a5a2a", hover_color="#3a8a3a"
                      ).pack(side="right", padx=(0,6), pady=10)

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=6)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)

        main = ctk.CTkFrame(body)
        main.grid(row=0, column=1, sticky="nsew", padx=(6,0))
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        tx_frame = ctk.CTkFrame(main)
        tx_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tx_frame.rowconfigure(1, weight=1)
        tx_frame.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(tx_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=(6,0))
        ctk.CTkLabel(hdr, text="Live Transcript",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self._wave_canvas = ctk.CTkCanvas(hdr, width=140, height=28,
                                           bg="#1a1a2e", highlightthickness=0)
        self._wave_canvas.pack(side="right", padx=8)
        self._wave_bars  = []
        self._wave_level = 0.0
        self._init_wave_canvas()

        self.transcript_text = ctk.CTkTextbox(
            tx_frame, font=ctk.CTkFont(family="Courier", size=font_size), wrap="word")
        self.transcript_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        ctrl = ctk.CTkFrame(main)
        ctrl.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,6))

        self.start_stop_button = ctk.CTkButton(
            ctrl, text="Start  (Ctrl+Space)", command=self.toggle_dictation,
            height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_stop_button.pack(side="left", padx=10, pady=10)

        ctk.CTkButton(ctrl, text="Save As", command=self.save_as,
                      height=40).pack(side="left", padx=6, pady=10)
        ctk.CTkButton(ctrl, text="Copy to Epic", command=self.copy_to_epic,
                      height=40, fg_color="#1a6b3c", hover_color="#23994f",
                      font=ctk.CTkFont(size=13, weight="bold")
                      ).pack(side="left", padx=6, pady=10)
        ctk.CTkButton(ctrl, text="Clear", command=self._clear_transcript,
                      height=40, fg_color="gray").pack(side="left", padx=6, pady=10)
        ctk.CTkButton(ctrl, text="Medical Terms", command=self.open_terms_manager,
                      height=40).pack(side="left", padx=6, pady=10)

        tmpl_names = list(all_templates().keys())
        self._tmpl_var = ctk.StringVar(value="Insert Template...")
        ctk.CTkOptionMenu(
            ctrl, values=tmpl_names, variable=self._tmpl_var,
            command=self._insert_template, width=170, height=40
        ).pack(side="left", padx=6, pady=10)
        ctk.CTkButton(ctrl, text="Save as Template", command=self._save_current_as_template,
                      height=40, fg_color="#444").pack(side="left", padx=6, pady=10)

        ctk.CTkButton(ctrl, text="Shortcuts (F1)", command=self._show_shortcuts_help,
                      height=40, fg_color="gray").pack(side="right", padx=10, pady=10)

        self.build_mic_settings(cfg.get("mic_index", 0))

        foot = ctk.CTkFrame(self)
        foot.pack(fill="x", padx=10, pady=(0,10))
        self._autosave_lbl = ctk.CTkLabel(foot, text="", justify="left", text_color="gray")
        self._autosave_lbl.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(foot, text=f"Output: {os.path.abspath(self.output_file)}",
                     justify="left").pack(side="left", padx=10, pady=8)
        ctk.CTkButton(foot, text="Open Folder",
                      command=self.open_output_folder, width=140).pack(side="right", padx=10, pady=8)

    # -- Sidebar with search --

    def _build_sidebar(self, parent):
        self._sidebar_visible = True
        self._sidebar = ctk.CTkFrame(parent, width=240)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._sidebar.rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 0))
        ctk.CTkLabel(hdr, text="Session History",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(hdr, text="\u00d7", width=28, height=28, fg_color="#333",
                      command=self._toggle_sidebar).pack(side="right")

        # Search bar
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        search_entry = ctk.CTkEntry(
            self._sidebar, textvariable=self._search_var,
            placeholder_text="Search sessions...", height=30
        )
        search_entry.grid(row=1, column=0, sticky="ew", padx=6, pady=(4, 2))

        self._session_scroll = ctk.CTkScrollableFrame(self._sidebar)
        self._session_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

        ctk.CTkButton(self._sidebar, text="+ New Session",
                      command=self._clear_transcript, fg_color="#333", height=30
                      ).grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 8))

        self._refresh_session_list()

        self._sidebar_toggle_btn = ctk.CTkButton(
            parent, text="\u2630 History", width=90, height=28, fg_color="#333",
            command=self._toggle_sidebar)

    def _on_search_changed(self, *_):
        query = self._search_var.get().strip()
        for w in self._session_scroll.winfo_children():
            w.destroy()
        if query:
            results = search_sessions(query, limit=50)
        else:
            results = list_sessions(50)
        if not results:
            ctk.CTkLabel(self._session_scroll,
                         text="No sessions found.",
                         text_color="gray",
                         font=ctk.CTkFont(size=11)).pack(pady=20)
            return
        for s in results:
            self._build_session_row(s)

    def _toggle_sidebar(self):
        if self._sidebar_visible:
            self._sidebar.grid_remove()
            self._sidebar_toggle_btn.grid(row=0, column=0, sticky="nw", padx=(0,4))
        else:
            self._sidebar_toggle_btn.grid_remove()
            self._sidebar.grid()
        self._sidebar_visible = not self._sidebar_visible

    def _refresh_session_list(self):
        for w in self._session_scroll.winfo_children():
            w.destroy()
        sessions = list_sessions(50)
        if not sessions:
            ctk.CTkLabel(self._session_scroll, text="No sessions yet.",
                         text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=20)
            return
        for s in sessions:
            self._build_session_row(s)

    def _build_session_row(self, s: dict):
        row = ctk.CTkFrame(self._session_scroll, fg_color="#222", corner_radius=6)
        row.pack(fill="x", padx=4, pady=3)
        dt  = s["started_at"][:16].replace("T", " ")
        dur = f"{int(s['duration_sec'] or 0)}s" if s.get("duration_sec") else "--"
        wc  = str(s.get("word_count") or 0) + "w"
        btn = ctk.CTkButton(row, text=f"{dt}\n{dur}  {wc}", anchor="w",
                            fg_color="transparent", hover_color="#333",
                            font=ctk.CTkFont(size=10),
                            command=lambda sid=s["id"], fp=s.get("file_path",""): self._load_session(sid, fp))
        btn.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        ctk.CTkButton(row, text="\u2715", width=24, height=24, fg_color="#5a1a1a",
                      hover_color="#8a2020",
                      command=lambda sid=s["id"]: self._delete_session(sid)
                      ).pack(side="right", padx=(0,4))

    def _load_session(self, session_id, file_path):
        text = read_transcript(file_path)
        self.transcript_text.delete("1.0", "end")
        self.transcript_text.insert("1.0", text or "[Session file not found]")
        self.update_status(f"Loaded session #{session_id}")

    def _delete_session(self, session_id):
        if messagebox.askyesno("Delete Session", f"Delete session #{session_id}?"):
            delete_session(session_id)
            self._refresh_session_list()

    # -- Waveform --

    def _init_wave_canvas(self):
        self._wave_canvas.delete("all")
        self._wave_bars = []
        n, w, h = 14, 140, 28
        bar_w = (w - (n+1)*2) // n
        for i in range(n):
            x1 = 2 + i*(bar_w+2)
            x2 = x1 + bar_w
            bar = self._wave_canvas.create_rectangle(x1, h//2, x2, h//2,
                                                     fill="#2b7cff", outline="")
            self._wave_bars.append((x1, x2, bar))

    def _start_waveform(self):
        self._wave_active = True
        self._animate_wave()

    def _stop_waveform(self):
        self._wave_active = False
        self._init_wave_canvas()

    def _animate_wave(self):
        if not getattr(self, "_wave_active", False):
            return
        import random
        level  = self._wave_level
        center = 14
        for x1, x2, bar in self._wave_bars:
            amp   = int(center * level * (0.4 + 0.6*random.random()))
            amp   = max(2, min(amp, center-1))
            color = "#d93025" if level > 0.8 else "#f0a500" if level > 0.5 else "#2ecc71"
            self._wave_canvas.coords(bar, x1, center-amp, x2, center+amp)
            self._wave_canvas.itemconfig(bar, fill=color)
        self.after(33, self._animate_wave)

    def _update_wave_level(self, level: float):
        self._wave_level = max(0.0, min(1.0, level))

    # -- Mic settings --

    def build_mic_settings(self, default_idx=0):
        mic_frame = ctk.CTkFrame(self)
        mic_frame.pack(fill="x", padx=10, pady=(0,4))
        ctk.CTkLabel(mic_frame, text="Microphone:").pack(side="left", padx=(10,5), pady=8)
        self.mic_var  = ctk.StringVar()
        self.mic_menu = ctk.CTkOptionMenu(mic_frame, variable=self.mic_var, width=260)
        self.mic_menu.pack(side="left", padx=5, pady=8)
        ctk.CTkButton(mic_frame, text="Refresh (F5)", command=self.refresh_mics, width=100).pack(side="left", padx=5)
        self.test_mic_btn = ctk.CTkButton(mic_frame, text="Test Mic",
                                           command=self.test_microphone, width=90)
        self.test_mic_btn.pack(side="left", padx=5)
        self.mic_level_label = ctk.CTkLabel(mic_frame, text="Level: --", width=100, anchor="w")
        self.mic_level_label.pack(side="left", padx=8)
        self.refresh_mics(select_idx=default_idx)

    def refresh_mics(self, select_idx=None):
        try:
            import sounddevice as sd
            opts = [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices())
                    if d["max_input_channels"] > 0]
            self.mic_menu.configure(values=opts or ["No microphones found"])
            match = next((o for o in opts if o.startswith(f"{select_idx}:")), opts[0] if opts else "")
            self.mic_var.set(match)
        except Exception as e:
            self.mic_menu.configure(values=[f"Error: {e}"])

    def test_microphone(self):
        try:
            import sounddevice as sd, numpy as np
            device_idx = int(self.mic_var.get().split(":")[0])
            self.test_mic_btn.configure(state="disabled")
            def run():
                try:
                    def cb(indata, frames, time, status):
                        level = float(np.linalg.norm(indata) / frames)
                        db    = 20 * math.log10(max(level, 0.001))
                        color = "green" if db > -40 else "orange" if db > -60 else "red"
                        self.after(0, lambda d=db, c=color:
                                   self.mic_level_label.configure(
                                       text=f"Level: {d:.0f} dB", text_color=c))
                    with sd.InputStream(device=device_idx, channels=1,
                                        samplerate=44100, callback=cb):
                        import time as _t; _t.sleep(3)
                except Exception as e:
                    self.after(0, lambda err=e:
                               messagebox.showerror("Mic Test Failed", str(err)))
                finally:
                    self.after(0, lambda: self.test_mic_btn.configure(state="normal"))
                    self.after(0, lambda: self.mic_level_label.configure(
                        text="Level: --", text_color="white"))
            threading.Thread(target=run, daemon=True).start()
            messagebox.showinfo("Mic Test", "Speak for 3 seconds...")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -- Templates --

    def _insert_template(self, name: str):
        body = get_template(name)
        if not body:
            return
        if self.transcript_text.get("1.0", "end-1c").strip():
            if not messagebox.askyesno("Insert Template",
                                       "Replace current transcript with template?"):
                return
        self.transcript_text.delete("1.0", "end")
        self.transcript_text.insert("1.0", body)
        self._tmpl_var.set("Insert Template...")
        self.update_status(f"Template inserted: {name}")

    def _save_current_as_template(self):
        body = self.transcript_text.get("1.0", "end-1c").strip()
        if not body:
            messagebox.showwarning("Empty", "Nothing in the transcript to save as a template.")
            return
        SaveTemplateDialog(self, body)

    # -- Dictation --

    def toggle_dictation(self):
        cfg = load_config()
        if not self.is_recording:
            Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
            self.start_stop_button.configure(text="Stop  (Ctrl+Space)", fg_color="#d93025")
            self.transcript_text.insert("end",
                f"\n--- Session started {datetime.now().strftime('%H:%M:%S')} ---\n")
            self._session_id = start_session(self.output_file)
            self.engine.start(self.output_file)
            self.is_recording = True
            self._start_waveform()
            self._attach_audio_level_hook()
            interval = cfg.get("autosave_interval", 60)
            self._autosaver = AutoSaver(
                get_transcript=lambda: self.transcript_text.get("1.0", "end-1c"),
                interval=interval
            )
            self._autosaver.on_save = lambda p: self.after(
                0, lambda path=p: self._autosave_lbl.configure(
                    text=f"Auto-saved {datetime.now().strftime('%I:%M %p')}"))
            self._autosaver.start()
            logger.info("Dictation started (session %s)", self._session_id)
        else:
            self.engine.stop()
            self._stop_waveform()
            if self._autosaver:
                self._autosaver.stop()
                self._autosaver = None
            self._autosave_lbl.configure(text="")
            self.start_stop_button.configure(text="Start  (Ctrl+Space)", fg_color="#2b7cff")
            self.transcript_text.insert("end",
                f"\n--- Session stopped {datetime.now().strftime('%H:%M:%S')} ---\n")
            transcript = self.transcript_text.get("1.0", "end-1c")
            if self._session_id:
                stop_session(self._session_id, transcript)
                self._session_id = None
            self.is_recording = False
            self.after(300, self._refresh_session_list)
            logger.info("Dictation stopped")

    def _attach_audio_level_hook(self):
        engine = self.engine
        app    = self
        import numpy as np
        orig = getattr(engine, "_sd_callback", None)
        def patched_cb(indata, frames, time, status):
            if orig:
                orig(indata, frames, time, status)
            level = float(np.linalg.norm(indata) / max(frames, 1))
            app._update_wave_level(min(level * 8, 1.0))
        def _hook():
            if engine.stream:
                engine.stream.callback = patched_cb
        self.after(200, _hook)

    # -- Dialogs --

    def open_settings(self):
        SettingsWindow(self, on_save=self._on_settings_saved)

    def _on_settings_saved(self, cfg):
        font_size = cfg.get("font_size", 13)
        self.transcript_text.configure(font=ctk.CTkFont(family="Courier", size=font_size))
        self._init_engine(cfg)
        self.update_status("Settings saved.")

    def open_finetune(self):
        FineTuneDialog(self)

    def open_about(self):
        AboutDialog(self, version=APP_VERSION)

    def copy_to_epic(self):
        transcript = self.transcript_text.get("1.0", "end-1c").strip()
        if not transcript:
            messagebox.showwarning("No Transcript", "Dictate something first!")
            return
        EpicExportDialog(self, transcript)

    def create_shortcut_manual(self):
        ok, msg = create_shortcut(silent=False)
        if ok:
            messagebox.showinfo("Shortcut Created", "Desktop shortcut created!")
        else:
            messagebox.showerror("Shortcut Failed", str(msg))

    def open_bug_report(self):
        BugReportDialog(parent=self)

    def open_view_log(self):
        ViewLogDialog(self)

    def _rerun_wizard(self):
        cfg = load_config()
        cfg["first_run_complete"] = False
        save_config(cfg)
        self.withdraw()
        OnboardingWizard(self, on_complete=self._wizard_done)

    def append_transcript(self, text: str):
        self.after(0, lambda t=text: self._safe_append(t))

    def _safe_append(self, text: str):
        self.transcript_text.insert("end", text + "\n")
        self.transcript_text.see("end")

    def update_status(self, msg: str):
        self.after(0, lambda m=msg: self.status_label.configure(text=f"Status: {m}"))

    def save_as(self):
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="chart_note.txt", title="Save Chart Note As...")
        if not fp:
            return
        try:
            Path(fp).write_text(self.transcript_text.get("1.0", "end-1c"), encoding="utf-8")
            messagebox.showinfo("Saved", f"Saved to {fp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_output_folder(self):
        folder = os.path.abspath(OUTPUT_DIR)
        system = platform.system()
        if system == "Windows":  os.startfile(folder)
        elif system == "Darwin": subprocess.Popen(["open", folder])
        else:                    subprocess.Popen(["xdg-open", folder])

    def open_terms_manager(self):
        # If already open, bring it to front instead of creating a second window
        if self._terms_window is not None and self._terms_window.winfo_exists():
            self._terms_window.lift()
            self._terms_window.focus_force()
            return
        self._terms_window = TermsManagerWindow(self)


# ---------------------------------------------------------------------------
#  Medical Terms Manager
# ---------------------------------------------------------------------------

class TermsManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Medical Terms")
        self.geometry("700x500")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _on_close(self):
        # Clear the parent's reference so the next click opens a fresh window
        if hasattr(self.master, "_terms_window"):
            self.master._terms_window = None
        self.destroy()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Add / Edit Medical Terms",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=10, pady=10)
        fields = [
            ("Correct Term",         "e.g., metformin"),
            ("Common Misrecognition", "e.g., met four min"),
            ("Category",             "medication / diagnosis / procedure"),
        ]
        self._entries: dict = {}
        for row, (label, ph) in enumerate(fields):
            ctk.CTkLabel(form, text=label, width=220, anchor="w").grid(
                row=row, column=0, padx=10, pady=5, sticky="w")
            e = ctk.CTkEntry(form, width=300, placeholder_text=ph)
            e.grid(row=row, column=1, padx=10, pady=5)
            self._entries[label] = e
        ctk.CTkButton(self, text="Add Term", command=self._add_term).pack(pady=10)
        ctk.CTkLabel(self, text="Tip: Run build_medical_db.py once to create the DB first.",
                     text_color="gray").pack(padx=10)

    def _add_term(self):
        term = self._entries["Correct Term"].get().strip()
        mis  = self._entries["Common Misrecognition"].get().strip()
        cat  = self._entries["Category"].get().strip()
        if not term:
            messagebox.showwarning("Missing", "Correct Term is required.")
            return
        import sqlite3
        db = Path("medical_terms.db")
        if not db.exists():
            messagebox.showerror("DB Missing", "Run build_medical_db.py first.")
            return
        conn = sqlite3.connect(str(db))
        try:
            conn.execute(
                "INSERT INTO terms (term, category, common_misrecognition) VALUES (?, ?, ?)",
                (term.lower(), cat or None, mis.lower() if mis else None))
            conn.commit()
            messagebox.showinfo("Added", f"Added: {term}")
            for e in self._entries.values():
                e.delete(0, "end")
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate", "Term already exists.")
        finally:
            conn.close()


if __name__ == "__main__":
    logger.info("Launching VoxChart %s", APP_VERSION)
    app = MedicalDictationApp()
    app.mainloop()
    logger.info("VoxChart exited cleanly")
