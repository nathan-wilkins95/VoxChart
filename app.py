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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

OUTPUT_DIR = "chart_notes"
DEFAULT_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "chart_note.txt")
APP_VERSION = "1.0.0"


class MedicalDictationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"VoxChart v{APP_VERSION}")
        self.geometry("900x700")

        app_dir = Path(__file__).parent
        model_path = app_dir / "models" / "large-v3-turbo"

        if model_path.exists() and len(list(model_path.iterdir())) > 10:
            model_loader = str(model_path)
            print(f"Using offline model from: {model_loader}")
        else:
            model_loader = "large-v3-turbo"
            print("No local model found, will download on first use")

        self.engine = DictationEngine(
            model_loader,
            device="cuda",
            compute_type="float16",
            output_dir=OUTPUT_DIR,
            corpus_dir="training_corpus",
        )
        self.engine.on_text_callback = self.append_transcript
        self.engine.on_status_callback = self.update_status

        self.output_file = DEFAULT_OUTPUT_FILE
        self.is_recording = False
        self.build_ui()

    def build_ui(self):
        top_frame = ctk.CTkFrame(self, corner_radius=0)
        top_frame.pack(fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(
            top_frame, text="Status: Ready  |  Device: CPU", justify="left"
        )
        self.status_label.pack(side="left", padx=10, pady=10)

        self.theme_var = ctk.StringVar(value="dark")
        theme_menu = ctk.CTkOptionMenu(
            top_frame,
            values=["system", "light", "dark"],
            variable=self.theme_var,
            command=self.change_theme,
            width=120,
        )
        theme_menu.pack(side="right", padx=10, pady=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        transcript_frame = ctk.CTkFrame(main_frame)
        transcript_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            transcript_frame,
            text="Live Transcript",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))
        self.transcript_text = ctk.CTkTextbox(
            transcript_frame, font=ctk.CTkFont(family="Courier", size=13), wrap="word"
        )
        self.transcript_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        controls_frame = ctk.CTkFrame(main_frame)
        controls_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.start_stop_button = ctk.CTkButton(
            controls_frame,
            text="Start Dictation",
            command=self.toggle_dictation,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_stop_button.pack(side="left", padx=10, pady=10)
        self.save_as_button = ctk.CTkButton(
            controls_frame, text="Save As...", command=self.save_as, height=40
        )
        self.save_as_button.pack(side="left", padx=10, pady=10)
        self.terms_button = ctk.CTkButton(
            controls_frame,
            text="Manage Medical Terms",
            command=self.open_terms_manager,
            height=40,
        )
        self.terms_button.pack(side="left", padx=10, pady=10)

        self.build_mic_settings()

        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(
            info_frame,
            text=f"Output: {os.path.abspath(self.output_file)}",
            justify="left",
        ).pack(side="left", padx=10, pady=10)
        self.open_folder_button = ctk.CTkButton(
            info_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            width=140,
        )
        self.open_folder_button.pack(side="right", padx=10, pady=10)

    def build_mic_settings(self):
        mic_frame = ctk.CTkFrame(self)
        mic_frame.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(mic_frame, text="Microphone:").pack(
            side="left", padx=(10, 5), pady=10
        )

        self.mic_var = ctk.StringVar()
        self.mic_menu = ctk.CTkOptionMenu(mic_frame, variable=self.mic_var, width=260)
        self.mic_menu.pack(side="left", padx=5, pady=10)

        refresh_btn = ctk.CTkButton(
            mic_frame, text="Refresh", command=self.refresh_mics, width=80
        )
        refresh_btn.pack(side="left", padx=5, pady=10)

        self.test_mic_btn = ctk.CTkButton(
            mic_frame, text="Test Mic", command=self.test_microphone, width=90
        )
        self.test_mic_btn.pack(side="left", padx=5, pady=10)

        self.mic_level_label = ctk.CTkLabel(
            mic_frame, text="Level: --", width=120, anchor="w"
        )
        self.mic_level_label.pack(side="left", padx=10, pady=10)

        self.refresh_mics()

    def refresh_mics(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            mic_options = [
                f"{i}: {d['name']}"
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
            if mic_options:
                self.mic_var.set(mic_options[0])
                self.mic_menu.configure(values=mic_options)
            else:
                self.mic_menu.configure(values=["No microphones found"])
                self.mic_var.set("No microphones found")
        except Exception as e:
            self.mic_menu.configure(values=[f"Error: {e}"])

    def test_microphone(self):
        try:
            import sounddevice as sd
            import numpy as np

            device_str = self.mic_var.get()
            device_idx = int(device_str.split(":")[0])
            fs = 16000
            self.mic_level_label.configure(text="Level: Testing...", text_color="gray")
            self.test_mic_btn.configure(state="disabled")

            def run_test():
                try:
                    def callback(indata, frames, time, status):
                        level = np.linalg.norm(indata) / frames
                        db = 20 * np.log10(max(0.001, level))
                        color = "green" if db > -40 else "orange" if db > -60 else "red"
                        label = f"Level: {db:.0f} dB"
                        self.after(0, lambda lbl=label, clr=color: self.mic_level_label.configure(
                            text=lbl, text_color=clr
                        ))

                    with sd.InputStream(
                        device=device_idx, channels=1, samplerate=fs, callback=callback
                    ):
                        import time
                        time.sleep(3)
                except Exception as e:
                    self.after(
                        0,
                        lambda err=e: messagebox.showerror(
                            "Mic Test Failed", f"Could not test microphone:\n{err}"
                        ),
                    )
                finally:
                    self.after(0, lambda: self.test_mic_btn.configure(state="normal"))
                    self.after(0, lambda: self.mic_level_label.configure(
                        text="Level: --", text_color="white"
                    ))

            threading.Thread(target=run_test, daemon=True).start()
            messagebox.showinfo("Mic Test", "Speak into your microphone for 3 seconds...")

        except Exception as e:
            messagebox.showerror("Error", f"Mic test error: {e}")

    def change_theme(self, choice: str):
        ctk.set_appearance_mode(choice)

    def toggle_dictation(self):
        if not self.is_recording:
            Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
            self.start_stop_button.configure(text="Stop Dictation", fg_color="#d93025")
            self.transcript_text.insert(
                "end",
                f"\n--- Session started {datetime.now().strftime('%H:%M:%S')} ---\n",
            )
            self.engine.start(self.output_file)
            self.is_recording = True
        else:
            self.engine.stop()
            self.start_stop_button.configure(text="Start Dictation", fg_color="#2b7cff")
            self.transcript_text.insert(
                "end",
                f"\n--- Session stopped {datetime.now().strftime('%H:%M:%S')} ---\n",
            )
            self.is_recording = False

    def append_transcript(self, text: str):
        self.after(0, lambda t=text: self.safe_append(t))

    def safe_append(self, text: str):
        self.transcript_text.insert("end", text)
        self.transcript_text.see("end")

    def update_status(self, msg: str):
        self.after(0, lambda m=msg: self.status_label.configure(text=f"Status: {m}"))

    def save_as(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="chart_note.txt",
            title="Save Chart Note As...",
        )
        if not filepath:
            return
        try:
            content = self.transcript_text.get("1.0", "end-1c")
            Path(filepath).write_text(content, encoding="utf-8")
            messagebox.showinfo("Saved", f"Chart note saved to {filepath}")
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


class TermsManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Medical Terms")
        self.geometry("700x500")
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(
            self,
            text="Add/Edit Medical Terms",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=10)

        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(form_frame, text="Correct Term (e.g., metformin)").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        self.term_entry = ctk.CTkEntry(form_frame, width=300)
        self.term_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Common Misrecognition (e.g., met four min)").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.mis_entry = ctk.CTkEntry(form_frame, width=300)
        self.mis_entry.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Category (medication/diagnosis/procedure)").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        self.cat_entry = ctk.CTkEntry(form_frame, width=300)
        self.cat_entry.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkButton(self, text="Add Term", command=self.add_term).pack(pady=10)

        ctk.CTkLabel(
            self,
            text="Tip: Run build_medical_db.py once to create the DB, then use this UI to add more terms.",
            justify="left",
            text_color="gray",
        ).pack(padx=10, pady=(0, 10))

    def add_term(self):
        term = self.term_entry.get().strip()
        mis = self.mis_entry.get().strip()
        cat = self.cat_entry.get().strip()

        if not term:
            messagebox.showwarning("Missing Field", "Correct Term is required.")
            return

        import sqlite3
        db_path = Path("medicalterms.db")
        if not db_path.exists():
            messagebox.showerror(
                "DB Missing",
                "Run build_medical_db.py first to create medicalterms.db",
            )
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
