import os
import sys
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from dictation_engine import DictationEngine

# ---------------- App Config ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_NAME   = "VoxChart"
APP_VER    = "1.0.0"
OUTPUT_DIR = "chart_notes"
DEFAULT_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "chart_note.txt")
MODEL_SIZE = "large-v3-turbo"

# Detect GPU — fall back to CPU gracefully
try:
    import torch
    _DEVICE       = "cuda" if torch.cuda.is_available() else "cpu"
    _COMPUTE_TYPE = "float16" if _DEVICE == "cuda" else "int8"
except ImportError:
    _DEVICE       = "cpu"
    _COMPUTE_TYPE = "int8"

# Fix Windows taskbar name — must be called before any Tk window is created.
if platform.system() == "Windows":
    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("VoxChart.App.1.0")
    except Exception:
        pass


def _ensure_db():
    """Create medical_terms.db automatically if it doesn't exist yet."""
    db_path = Path("medical_terms.db")
    if not db_path.exists():
        try:
            import build_medical_db
        except Exception:
            pass


def _check_microphone() -> bool:
    """Return True if at least one input device is available."""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        found = any(
            p.get_device_info_by_index(i).get("maxInputChannels", 0) > 0
            for i in range(p.get_device_count())
        )
        p.terminate()
        return found
    except Exception:
        return True  # If PyAudio itself fails, let DictationEngine surface the real error


def _friendly_model_error(err: str) -> str:
    """Return a user-friendly error message based on the exception text."""
    e = err.lower()
    if any(k in e for k in ("connection", "download", "network", "timeout", "urllib", "requests", "ssl")):
        return (
            "VoxChart could not download the AI model.\n\n"
            "Please check your internet connection and try again.\n"
            "If you are behind a firewall or proxy, contact your IT department."
        )
    if any(k in e for k in ("cuda", "gpu", "cudnn", "nccl")):
        return (
            f"GPU error encountered — falling back may help.\n\n"
            f"Technical detail: {err}\n\n"
            f"Device: {_DEVICE}  |  Compute: {_COMPUTE_TYPE}"
        )
    if any(k in e for k in ("memory", "oom", "out of memory")):
        return (
            "VoxChart ran out of memory loading the AI model.\n\n"
            "Try closing other applications and restarting VoxChart."
        )
    return (
        f"Failed to load AI model:\n\n{err}\n\n"
        f"Device: {_DEVICE}  |  Compute: {_COMPUTE_TYPE}"
    )


# ---------------- First-Run Download Dialog ----------------

class FirstRunDialog(tk.Toplevel):
    """Shown on first launch while the Whisper model downloads."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("VoxChart — First Run Setup")
        self.geometry("460x200")
        self.configure(bg="#1c1b19")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent close

        ctk.CTkLabel(
            self,
            text="Downloading AI Model (first run only)",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            self,
            text=f"Downloading {MODEL_SIZE} — this may take a few minutes.\nThe app will open automatically when ready.",
            justify="center",
            text_color="gray"
        ).pack(pady=(0, 14))

        self.progress = ctk.CTkProgressBar(self, width=380, mode="indeterminate")
        self.progress.pack(pady=4)
        self.progress.start()

        self.status_label = ctk.CTkLabel(self, text="Connecting...", text_color="gray")
        self.status_label.pack(pady=6)

    def set_status(self, msg: str):
        self.status_label.configure(text=msg)
        self.update_idletasks()


# ---------------- Main App ----------------

class VoxChartApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("900x650")
        self.withdraw()  # hide until model is ready

        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

        self.is_recording = False
        self.output_file  = DEFAULT_OUTPUT_FILE

        self._first_run_dlg = None
        self._load_model_async()

    def _load_model_async(self):
        """Load the Whisper model on a background thread; show progress dialog."""
        import faster_whisper
        model_cache = Path.home() / ".cache" / "huggingface" / "hub"
        already_cached = any(model_cache.rglob(f"*{MODEL_SIZE}*")) if model_cache.exists() else False

        if not already_cached:
            self._first_run_dlg = FirstRunDialog(self)

        def _do_load():
            try:
                self.engine = DictationEngine(
                    model_size=MODEL_SIZE,
                    device=_DEVICE,
                    compute_type=_COMPUTE_TYPE,
                    output_dir=OUTPUT_DIR,
                    corpus_dir="training_corpus"
                )
                self.engine.on_text_callback   = self.append_transcript
                self.engine.on_status_callback = self.update_status
                self.after(0, self._on_model_ready)
            except Exception as e:
                self.after(0, lambda: self._on_model_error(str(e)))

        threading.Thread(target=_do_load, daemon=True).start()

    def _on_model_ready(self):
        if self._first_run_dlg:
            self._first_run_dlg.destroy()
            self._first_run_dlg = None
        _ensure_db()

        # Microphone check — warn but don't block; user may plug in later
        if not _check_microphone():
            messagebox.showwarning(
                "No Microphone Found",
                "VoxChart could not detect a microphone.\n\n"
                "Please connect a microphone and restart the app before dictating."
            )

        self._build_ui()
        self.deiconify()

    def _on_model_error(self, err: str):
        if self._first_run_dlg:
            self._first_run_dlg.destroy()
        messagebox.showerror("VoxChart — Startup Error", _friendly_model_error(err))
        self.destroy()

    def _build_ui(self):
        top_frame = ctk.CTkFrame(self, corner_radius=0)
        top_frame.pack(fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(
            top_frame,
            text=f"Status: Ready  |  Device: {_DEVICE.upper()}",
            justify="left"
        )
        self.status_label.pack(side="left", padx=10, pady=10)

        self.theme_var = ctk.StringVar(value="dark")
        theme_menu = ctk.CTkOptionMenu(
            top_frame,
            values=["system", "light", "dark"],
            variable=self.theme_var,
            command=self.change_theme,
            width=120
        )
        theme_menu.pack(side="right", padx=10, pady=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        transcript_frame = ctk.CTkFrame(main_frame)
        transcript_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            transcript_frame,
            text="Live Transcript",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.transcript_text = ctk.CTkTextbox(
            transcript_frame,
            font=ctk.CTkFont(family="Courier", size=13),
            wrap="word"
        )
        self.transcript_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        controls_frame = ctk.CTkFrame(main_frame)
        controls_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.start_stop_button = ctk.CTkButton(
            controls_frame,
            text="Start Dictation",
            command=self.toggle_dictation,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_stop_button.pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            controls_frame,
            text="Save As...",
            command=self.save_as,
            height=40
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            controls_frame,
            text="Manage Medical Terms",
            command=self.open_terms_manager,
            height=40
        ).pack(side="left", padx=10, pady=10)

        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            info_frame,
            text=f"Output: {os.path.abspath(self.output_file)}",
            justify="left"
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(
            info_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            width=140
        ).pack(side="right", padx=10, pady=10)

    # ---------------- Callbacks ----------------

    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)

    def toggle_dictation(self):
        if not self.is_recording:
            Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
            self.start_stop_button.configure(text="Stop Dictation", fg_color="#d93025")
            self.transcript_text.insert("end", f"\n--- Session started {datetime.now().strftime('%H:%M:%S')} ---\n")
            self.engine.start(self.output_file)
            self.is_recording = True
        else:
            self.engine.stop()
            self.start_stop_button.configure(text="Start Dictation", fg_color="#2b7cff")
            self.transcript_text.insert("end", f"\n--- Session stopped {datetime.now().strftime('%H:%M:%S')} ---\n\n")
            self.is_recording = False

    def append_transcript(self, text):
        self.after(0, lambda: self._safe_append(text))

    def _safe_append(self, text):
        self.transcript_text.insert("end", text + "\n")
        self.transcript_text.see("end")

    def update_status(self, msg):
        self.after(0, lambda: self.status_label.configure(
            text=f"Status: {msg}  |  Device: {_DEVICE.upper()}"
        ))

    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension="",
            filetypes=[("All files", "*.*"), ("Text files", "*.txt"), ("Word docs", "*.docx")],
            initialfile="chart_note",
            title="Save Chart Note As"
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(self.transcript_text.get("1.0", "end-1c"), encoding="utf-8")
            messagebox.showinfo("Saved", f"Chart note saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def open_output_folder(self):
        folder = os.path.abspath(OUTPUT_DIR)
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def open_terms_manager(self):
        TermsManagerWindow(self)


# ---------------- Terms Manager Window ----------------

class TermsManagerWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("VoxChart — Manage Medical Terms")
        self.geometry("700x520")
        self.configure(bg="#2b2b2b")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="Add / Edit Medical Terms",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

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

        ctk.CTkLabel(
            self,
            text="Terms are saved to medical_terms.db and used automatically during transcription.",
            justify="left",
            text_color="gray"
        ).pack(padx=10, pady=(0, 10))

    def add_term(self):
        term = self.term_entry.get().strip()
        mis  = self.mis_entry.get().strip()
        cat  = self.cat_entry.get().strip()

        if not term:
            messagebox.showwarning("Missing Field", "Correct Term is required.", parent=self)
            return

        import sqlite3
        db_path = Path("medical_terms.db")
        if not db_path.exists():
            try:
                import build_medical_db
            except Exception as e:
                messagebox.showerror("DB Error", f"Could not create database:\n{e}", parent=self)
                return

        conn = sqlite3.connect(str(db_path))
        cur  = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO terms (term, category, common_misrecognition) VALUES (?, ?, ?)",
                (term.lower(), cat or None, mis.lower() if mis else None)
            )
            conn.commit()
            messagebox.showinfo("Success", f"Added term: {term}", parent=self)
            self.term_entry.delete(0, "end")
            self.mis_entry.delete(0, "end")
            self.cat_entry.delete(0, "end")
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate", "This term already exists.", parent=self)
        finally:
            conn.close()


if __name__ == "__main__":
    app = VoxChartApp()
    app.mainloop()
