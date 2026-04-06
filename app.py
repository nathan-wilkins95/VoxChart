import os
import sys
import json
import platform
import subprocess
import threading
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from dictation_engine import DictationEngine
from epic_exporter import format_for_epic, copy_to_clipboard, export_to_file
from shortcut_utils import create_shortcut, shortcut_already_exists

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

OUTPUT_DIR = "chart_notes"
DEFAULT_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "chart_note.txt")
APP_VERSION = "1.3.0"
CONFIG_FILE = Path("voxchart_config.json")


def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def detect_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return True, name
    except Exception:
        pass
    return False, None


# ──────────────────────────────────────────────
#  First-Run Onboarding Wizard
# ──────────────────────────────────────────────

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
        self.chosen_device = ctk.StringVar(value="cuda" if self.gpu_available else "cpu")
        self.chosen_mic_idx = ctk.IntVar(value=0)
        self.chosen_mic_name = ctk.StringVar(value="")

        self.frames = []
        self._build_steps()
        self._show_step(0)

    def _build_steps(self):
        self.frames = [
            self._build_welcome(),
            self._build_device_step(),
            self._build_mic_step(),
        ]

    def _build_welcome(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Welcome to VoxChart",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(40, 10))
        ctk.CTkLabel(f, text=(
            "VoxChart turns your voice into structured medical chart notes\n"
            "using a fully offline AI - no internet required after setup.\n\n"
            "This wizard will configure your microphone and compute device.\n"
            "It only runs once."
        ), font=ctk.CTkFont(size=13), justify="center").pack(pady=10, padx=30)
        ctk.CTkLabel(f, text="Click Next to begin",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(20, 0))
        self._nav_buttons(f, back=False)
        return f

    def _build_device_step(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Step 1 of 2 - Compute Device",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(30, 10))
        if self.gpu_available:
            gpu_label = f"GPU detected: {self.gpu_name}"
            gpu_color, rec_text = "green", "GPU recommended - faster transcription."
        else:
            gpu_label = "No NVIDIA GPU detected"
            gpu_color, rec_text = "orange", "CPU mode will be used. Transcription may be slower."
        ctk.CTkLabel(f, text=gpu_label,
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=gpu_color).pack(pady=(10, 4))
        ctk.CTkLabel(f, text=rec_text,
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 20))
        ctk.CTkLabel(f, text="Select compute device:", font=ctk.CTkFont(size=13)).pack()
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkRadioButton(btn_frame, text="GPU (CUDA) - fast, requires NVIDIA GPU",
                           variable=self.chosen_device, value="cuda",
                           state="normal" if self.gpu_available else "disabled").pack(anchor="w", padx=20, pady=6)
        ctk.CTkRadioButton(btn_frame, text="CPU - works on any machine, slower",
                           variable=self.chosen_device, value="cpu").pack(anchor="w", padx=20, pady=6)
        if not self.gpu_available:
            self.chosen_device.set("cpu")
        self._nav_buttons(f)
        return f

    def _build_mic_step(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Step 2 of 2 - Microphone",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(30, 10))
        ctk.CTkLabel(f, text="Select the microphone you will use for dictation.",
                     font=ctk.CTkFont(size=13)).pack(pady=(0, 10))
        self.wizard_mic_var = ctk.StringVar()
        self.wizard_mic_menu = ctk.CTkOptionMenu(f, variable=self.wizard_mic_var, width=380)
        self.wizard_mic_menu.pack(pady=6)
        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(pady=6)
        ctk.CTkButton(btn_row, text="Refresh", command=self._refresh_wizard_mics, width=90).pack(side="left", padx=6)
        self.wizard_test_btn = ctk.CTkButton(btn_row, text="Test Mic",
                                              command=self._test_wizard_mic, width=90)
        self.wizard_test_btn.pack(side="left", padx=6)
        self.wizard_level_label = ctk.CTkLabel(f, text="Level: --",
                                                font=ctk.CTkFont(size=12), text_color="gray")
        self.wizard_level_label.pack(pady=4)
        self._refresh_wizard_mics()
        self._nav_buttons(f, next_text="Finish")
        return f

    def _refresh_wizard_mics(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            opts = [f"{i}: {d['name']}" for i, d in enumerate(devices) if d["max_input_channels"] > 0]
            if opts:
                self.wizard_mic_var.set(opts[0])
                self.wizard_mic_menu.configure(values=opts)
            else:
                self.wizard_mic_var.set("No microphones found")
                self.wizard_mic_menu.configure(values=["No microphones found"])
        except Exception as e:
            self.wizard_mic_menu.configure(values=[f"Error: {e}"])

    def _test_wizard_mic(self):
        try:
            import sounddevice as sd
            import numpy as np
            device_idx = int(self.wizard_mic_var.get().split(":")[0])
            self.wizard_level_label.configure(text="Level: testing...", text_color="gray")
            self.wizard_test_btn.configure(state="disabled")
            def run():
                try:
                    def cb(indata, frames, time, status):
                        level = float(np.linalg.norm(indata) / frames)
                        db = 20 * (level and __import__('math').log10(max(level, 0.001)))
                        color = "green" if db > -40 else "orange" if db > -60 else "red"
                        self.after(0, lambda d=db, c=color: self.wizard_level_label.configure(
                            text=f"Level: {d:.0f} dB", text_color=c))
                    with sd.InputStream(device=device_idx, channels=1, samplerate=16000, callback=cb):
                        import time as _t; _t.sleep(3)
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("Mic Test Failed", str(err)))
                finally:
                    self.after(0, lambda: self.wizard_test_btn.configure(state="normal"))
                    self.after(0, lambda: self.wizard_level_label.configure(text="Level: --", text_color="gray"))
            threading.Thread(target=run, daemon=True).start()
            messagebox.showinfo("Mic Test", "Speak for 3 seconds...")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _nav_buttons(self, parent, back=True, next_text="Next"):
        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(side="bottom", fill="x", padx=20, pady=20)
        if back:
            ctk.CTkButton(nav, text="Back", width=100, fg_color="gray",
                          command=lambda: self._show_step(self.step - 1)).pack(side="left")
        ctk.CTkButton(nav, text=next_text, width=120,
                      command=self._next_or_finish).pack(side="right")

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
            mic_idx = int(mic_str.split(":")[0])
            mic_name = mic_str.split(":", 1)[1].strip()
        except Exception:
            mic_idx = 0
            mic_name = mic_str
        cfg = {
            "first_run_complete": True,
            "device": self.chosen_device.get(),
            "compute_type": "float16" if self.chosen_device.get() == "cuda" else "int8",
            "mic_index": mic_idx,
            "mic_name": mic_name,
        }
        save_config(cfg)
        self.grab_release()
        self.destroy()
        self.on_complete(cfg)


# ──────────────────────────────────────────────
#  Epic Export Dialog
# ──────────────────────────────────────────────

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
        fields = [
            ("Provider Name", "e.g., Dr. Smith"),
            ("Patient Name",  "e.g., John Doe"),
            ("Date of Birth", "e.g., 01/15/1970"),
            ("MRN",           "e.g., 123456"),
        ]
        self._entries: dict[str, ctk.CTkEntry] = {}
        for row, (label, placeholder) in enumerate(fields):
            ctk.CTkLabel(form, text=label, width=130, anchor="w").grid(
                row=row, column=0, padx=(0, 10), pady=6, sticky="w")
            entry = ctk.CTkEntry(form, width=260, placeholder_text=placeholder)
            entry.grid(row=row, column=1, pady=6)
            self._entries[label] = entry
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", width=100,
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="Copy to Epic Clipboard", width=220,
                      command=self._export).pack(side="right")

    def _export(self):
        formatted = format_for_epic(
            self.transcript,
            provider_name=self._entries["Provider Name"].get().strip(),
            patient_name=self._entries["Patient Name"].get().strip(),
            dob=self._entries["Date of Birth"].get().strip(),
            mrn=self._entries["MRN"].get().strip(),
        )
        saved_path = export_to_file(formatted)
        copy_to_clipboard(formatted)
        self.grab_release()
        self.destroy()
        messagebox.showinfo("Copied!",
            f"Epic note copied to clipboard!\n\n"
            f"1. Open Epic\n2. Open your note field\n3. Press Ctrl+V\n\n"
            f"Also saved to:\n{saved_path}")


# ──────────────────────────────────────────────
#  Main App
# ──────────────────────────────────────────────

class MedicalDictationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"VoxChart v{APP_VERSION}")
        self.geometry("950x720")
        self.output_file = DEFAULT_OUTPUT_FILE
        self.is_recording = False
        self.engine = None

        cfg = load_config()
        if not cfg.get("first_run_complete"):
            self.withdraw()
            self.after(200, self._run_wizard)
        else:
            self._init_engine(cfg)
            self.build_ui()
            self._bind_shortcuts()
            # Auto-create shortcut silently if never done before
            if not shortcut_already_exists():
                self.after(1500, self._auto_create_shortcut)

    def _auto_create_shortcut(self):
        ok, msg = create_shortcut(silent=True)
        if ok:
            self.update_status("Desktop shortcut created automatically.")

    def _bind_shortcuts(self):
        self.bind("<Control-space>", lambda e: self.toggle_dictation())
        self.bind("<Control-s>", lambda e: self.save_as())
        self.bind("<Control-o>", lambda e: self.open_output_folder())
        self.bind("<Control-e>", lambda e: self.copy_to_epic())
        self.bind("<Escape>", lambda e: self._clear_transcript())
        self.bind("<F1>", lambda e: self._show_shortcuts_help())
        self.bind("<F5>", lambda e: self.refresh_mics())

    def _clear_transcript(self):
        if not self.is_recording:
            self.transcript_text.delete("1.0", "end")
            self.update_status("Transcript cleared.")

    def _show_shortcuts_help(self):
        messagebox.showinfo("Keyboard Shortcuts",
            "VoxChart Keyboard Shortcuts\n\n"
            "Ctrl + Space   ->  Start / Stop Dictation\n"
            "Ctrl + S       ->  Save As...\n"
            "Ctrl + E       ->  Copy to Epic\n"
            "Ctrl + O       ->  Open Output Folder\n"
            "Esc            ->  Clear Transcript (when stopped)\n"
            "F1             ->  Show This Help\n"
            "F5             ->  Refresh Microphone List\n"
        )

    def _run_wizard(self):
        OnboardingWizard(self, on_complete=self._wizard_done)

    def _wizard_done(self, cfg):
        self._init_engine(cfg)
        self.build_ui()
        self._bind_shortcuts()
        self.deiconify()
        if not shortcut_already_exists():
            self.after(1500, self._auto_create_shortcut)

    def _init_engine(self, cfg):
        self.engine = DictationEngine(
            model_size="large-v3-turbo",
            device=cfg.get("device", "cpu"),
            compute_type=cfg.get("compute_type", "int8"),
            output_dir=OUTPUT_DIR,
            corpus_dir="training_corpus",
        )
        self.engine.on_text_callback = self.append_transcript
        self.engine.on_status_callback = self.update_status
        self._cfg = cfg

    def build_ui(self):
        cfg = self._cfg
        device_label = "GPU (CUDA)" if cfg.get("device") == "cuda" else "CPU"
        mic_name = cfg.get("mic_name", "Default")

        # Top bar
        top_frame = ctk.CTkFrame(self, corner_radius=0)
        top_frame.pack(fill="x", padx=10, pady=10)
        self.status_label = ctk.CTkLabel(
            top_frame,
            text=f"Status: Ready  |  Device: {device_label}  |  Mic: {mic_name}  |  F1 = Shortcuts",
            justify="left",
        )
        self.status_label.pack(side="left", padx=10, pady=10)
        self.theme_var = ctk.StringVar(value="dark")
        ctk.CTkOptionMenu(top_frame, values=["system", "light", "dark"],
                          variable=self.theme_var, command=self.change_theme,
                          width=120).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(top_frame, text="Re-run Setup", command=self._rerun_wizard,
                      width=110, fg_color="gray").pack(side="right", padx=(0, 6), pady=10)
        # Create Shortcut button
        ctk.CTkButton(
            top_frame,
            text="Pin to Desktop",
            command=self.create_shortcut_manual,
            width=120,
            fg_color="#444",
            hover_color="#666",
        ).pack(side="right", padx=(0, 6), pady=10)

        # Main area
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        transcript_frame = ctk.CTkFrame(main_frame)
        transcript_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(transcript_frame, text="Live Transcript",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.transcript_text = ctk.CTkTextbox(transcript_frame,
                                               font=ctk.CTkFont(family="Courier", size=13), wrap="word")
        self.transcript_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Controls row
        controls_frame = ctk.CTkFrame(main_frame)
        controls_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.start_stop_button = ctk.CTkButton(
            controls_frame, text="Start  (Ctrl+Space)",
            command=self.toggle_dictation, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_stop_button.pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text="Save As  (Ctrl+S)",
                      command=self.save_as, height=40).pack(side="left", padx=6, pady=10)
        ctk.CTkButton(
            controls_frame, text="Copy to Epic  (Ctrl+E)",
            command=self.copy_to_epic, height=40,
            fg_color="#1a6b3c", hover_color="#23994f",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=6, pady=10)
        ctk.CTkButton(controls_frame, text="Clear  (Esc)",
                      command=self._clear_transcript, height=40,
                      fg_color="gray").pack(side="left", padx=6, pady=10)
        ctk.CTkButton(controls_frame, text="Manage Medical Terms",
                      command=self.open_terms_manager, height=40).pack(side="left", padx=6, pady=10)
        ctk.CTkButton(controls_frame, text="Shortcuts  (F1)",
                      command=self._show_shortcuts_help, height=40,
                      fg_color="gray").pack(side="right", padx=10, pady=10)

        self.build_mic_settings(cfg.get("mic_index", 0))

        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(info_frame, text=f"Output: {os.path.abspath(self.output_file)}",
                     justify="left").pack(side="left", padx=10, pady=10)
        ctk.CTkButton(info_frame, text="Open Folder  (Ctrl+O)",
                      command=self.open_output_folder, width=180).pack(side="right", padx=10, pady=10)

    def build_mic_settings(self, default_idx=0):
        mic_frame = ctk.CTkFrame(self)
        mic_frame.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(mic_frame, text="Microphone:").pack(side="left", padx=(10, 5), pady=10)
        self.mic_var = ctk.StringVar()
        self.mic_menu = ctk.CTkOptionMenu(mic_frame, variable=self.mic_var, width=260)
        self.mic_menu.pack(side="left", padx=5, pady=10)
        ctk.CTkButton(mic_frame, text="Refresh (F5)", command=self.refresh_mics,
                      width=100).pack(side="left", padx=5, pady=10)
        self.test_mic_btn = ctk.CTkButton(mic_frame, text="Test Mic",
                                          command=self.test_microphone, width=90)
        self.test_mic_btn.pack(side="left", padx=5, pady=10)
        self.mic_level_label = ctk.CTkLabel(mic_frame, text="Level: --", width=120, anchor="w")
        self.mic_level_label.pack(side="left", padx=10, pady=10)
        self.refresh_mics(select_idx=default_idx)

    def refresh_mics(self, select_idx=None):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            opts = [f"{i}: {d['name']}" for i, d in enumerate(devices) if d["max_input_channels"] > 0]
            if opts:
                self.mic_menu.configure(values=opts)
                match = next((o for o in opts if o.startswith(f"{select_idx}:")), opts[0]) if select_idx is not None else opts[0]
                self.mic_var.set(match)
            else:
                self.mic_menu.configure(values=["No microphones found"])
                self.mic_var.set("No microphones found")
        except Exception as e:
            self.mic_menu.configure(values=[f"Error: {e}"])

    def test_microphone(self):
        try:
            import sounddevice as sd
            import numpy as np
            device_idx = int(self.mic_var.get().split(":")[0])
            self.mic_level_label.configure(text="Level: testing...", text_color="gray")
            self.test_mic_btn.configure(state="disabled")
            def run():
                try:
                    def cb(indata, frames, time, status):
                        level = float(np.linalg.norm(indata) / frames)
                        import math
                        db = 20 * math.log10(max(level, 0.001))
                        color = "green" if db > -40 else "orange" if db > -60 else "red"
                        self.after(0, lambda d=db, c=color: self.mic_level_label.configure(
                            text=f"Level: {d:.0f} dB", text_color=c))
                    with sd.InputStream(device=device_idx, channels=1, samplerate=16000, callback=cb):
                        import time as _t; _t.sleep(3)
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("Mic Test Failed", str(err)))
                finally:
                    self.after(0, lambda: self.test_mic_btn.configure(state="normal"))
                    self.after(0, lambda: self.mic_level_label.configure(text="Level: --", text_color="white"))
            threading.Thread(target=run, daemon=True).start()
            messagebox.showinfo("Mic Test", "Speak into your microphone for 3 seconds...")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _rerun_wizard(self):
        cfg = load_config()
        cfg["first_run_complete"] = False
        save_config(cfg)
        self.withdraw()
        OnboardingWizard(self, on_complete=self._wizard_done)

    def change_theme(self, choice: str):
        ctk.set_appearance_mode(choice)

    def toggle_dictation(self):
        if not self.is_recording:
            Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
            self.start_stop_button.configure(text="Stop  (Ctrl+Space)", fg_color="#d93025")
            self.transcript_text.insert("end", f"\n--- Session started {datetime.now().strftime('%H:%M:%S')} ---\n")
            self.engine.start(self.output_file)
            self.is_recording = True
        else:
            self.engine.stop()
            self.start_stop_button.configure(text="Start  (Ctrl+Space)", fg_color="#2b7cff")
            self.transcript_text.insert("end", f"\n--- Session stopped {datetime.now().strftime('%H:%M:%S')} ---\n")
            self.is_recording = False

    def copy_to_epic(self):
        transcript = self.transcript_text.get("1.0", "end-1c").strip()
        if not transcript:
            messagebox.showwarning("No Transcript", "Nothing to export. Dictate something first!")
            return
        EpicExportDialog(self, transcript)

    def create_shortcut_manual(self):
        """Manually triggered from the Pin to Desktop button."""
        ok, msg = create_shortcut(silent=False)
        if ok:
            messagebox.showinfo("Shortcut Created",
                f"Desktop shortcut created successfully!\n\n"
                f"You can now launch VoxChart directly from your desktop.")
        else:
            messagebox.showerror("Shortcut Failed", f"Could not create shortcut:\n{msg}")

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
            initialfile="chart_note.txt", title="Save Chart Note As...",
        )
        if not fp:
            return
        try:
            Path(fp).write_text(self.transcript_text.get("1.0", "end-1c"), encoding="utf-8")
            messagebox.showinfo("Saved", f"Chart note saved to {fp}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")

    def open_output_folder(self):
        folder = os.path.abspath(OUTPUT_DIR)
        system = platform.system()
        if system == "Windows":
            os.startfile(folder)
        elif system == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def open_terms_manager(self):
        TermsManagerWindow(self)


# ──────────────────────────────────────────────
#  Medical Terms Manager
# ──────────────────────────────────────────────

class TermsManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Medical Terms")
        self.geometry("700x500")
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="Add/Edit Medical Terms",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(form_frame, text="Correct Term (e.g., metformin)").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.term_entry = ctk.CTkEntry(form_frame, width=300)
        self.term_entry.grid(row=0, column=1, padx=10, pady=5)
        ctk.CTkLabel(form_frame, text="Common Misrecognition (e.g., met four min)").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.mis_entry = ctk.CTkEntry(form_frame, width=300)
        self.mis_entry.grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(form_frame, text="Category (medication/diagnosis/procedure)").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.cat_entry = ctk.CTkEntry(form_frame, width=300)
        self.cat_entry.grid(row=2, column=1, padx=10, pady=5)
        ctk.CTkButton(self, text="Add Term", command=self.add_term).pack(pady=10)
        ctk.CTkLabel(self,
                     text="Tip: Run build_medical_db.py once to create the DB, then use this UI to add more terms.",
                     justify="left", text_color="gray").pack(padx=10, pady=(0, 10))

    def add_term(self):
        term = self.term_entry.get().strip()
        mis = self.mis_entry.get().strip()
        cat = self.cat_entry.get().strip()
        if not term:
            messagebox.showwarning("Missing Field", "Correct Term is required.")
            return
        import sqlite3
        db_path = Path("medical_terms.db")
        if not db_path.exists():
            messagebox.showerror("DB Missing", "Run build_medical_db.py first.")
            return
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO terms (term, category, common_misrecognition) VALUES (?, ?, ?)",
                (term.lower(), cat or None, mis.lower() if mis else None),
            )
            conn.commit()
            messagebox.showinfo("Success", f"Added term: {term}")
            self.term_entry.delete(0, "end")
            self.mis_entry.delete(0, "end")
            self.cat_entry.delete(0, "end")
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate", "This term already exists.")
        finally:
            conn.close()


if __name__ == "__main__":
    app = MedicalDictationApp()
    app.mainloop()
