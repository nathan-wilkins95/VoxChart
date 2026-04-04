import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from dictation_engine import DictationEngine

# ---------------- App Config ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_NAME    = "VoxChart"
OUTPUT_DIR  = "chart_notes"
DEFAULT_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "chart_note.txt")

# Fix Windows taskbar name — must be called before any Tk window is created.
if platform.system() == "Windows":
    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "VoxChart.App.1.0"
        )
    except Exception:
        pass


class VoxChartApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("900x650")

        # Set taskbar / window icon
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

        self.engine = DictationEngine(
            model_size="large-v3-turbo",
            device="cuda",
            compute_type="float16",
            output_dir=OUTPUT_DIR,
            corpus_dir="training_corpus"
        )
        self.engine.on_text_callback = self.append_transcript
        self.engine.on_status_callback = self.update_status

        self.output_file = DEFAULT_OUTPUT_FILE
        self.is_recording = False

        self._build_ui()

    def _build_ui(self):
        # Top bar
        top_frame = ctk.CTkFrame(self, corner_radius=0)
        top_frame.pack(fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(
            top_frame,
            text="Status: Ready (model not loaded)",
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

        # Main area
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Transcript area
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

        # Controls
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

        self.save_as_button = ctk.CTkButton(
            controls_frame,
            text="Save As...",
            command=self.save_as,
            height=40
        )
        self.save_as_button.pack(side="left", padx=10, pady=10)

        self.terms_button = ctk.CTkButton(
            controls_frame,
            text="Manage Medical Terms",
            command=self.open_terms_manager,
            height=40
        )
        self.terms_button.pack(side="left", padx=10, pady=10)

        # Bottom info bar
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            info_frame,
            text=f"Output file: {os.path.abspath(self.output_file)}",
            justify="left"
        ).pack(side="left", padx=10, pady=10)

        self.open_folder_button = ctk.CTkButton(
            info_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            width=140
        )
        self.open_folder_button.pack(side="right", padx=10, pady=10)

    # ---------------- Callbacks ----------------

    def change_theme(self, choice: str):
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

    def append_transcript(self, text: str):
        self.after(0, lambda: self._safe_append(text))

    def _safe_append(self, text: str):
        self.transcript_text.insert("end", text + "\n")
        self.transcript_text.see("end")

    def update_status(self, msg: str):
        self.after(0, lambda: self.status_label.configure(text=f"Status: {msg}"))

    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension="",
            filetypes=[
                ("All files",  "*.*"),
                ("Text files", "*.txt"),
                ("Word docs",  "*.docx"),
            ],
            initialfile="chart_note",
            title="Save Chart Note As"
        )
        if not file_path:
            return
        try:
            content = self.transcript_text.get("1.0", "end-1c")
            Path(file_path).write_text(content, encoding="utf-8")
            messagebox.showinfo("Saved", f"Chart note saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

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


# ---------------- Medical Terms Manager Window ----------------

class TermsManagerWindow(tk.Toplevel):
    """Uses tk.Toplevel (not CTkToplevel) to avoid the Windows focus/close bug."""
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

        ctk.CTkLabel(form_frame, text="Correct Term (e.g., metformin)").grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        self.term_entry = ctk.CTkEntry(form_frame, width=300)
        self.term_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Common Misrecognition (e.g., met four min)").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        self.mis_entry = ctk.CTkEntry(form_frame, width=300)
        self.mis_entry.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(form_frame, text="Category (medication/diagnosis/procedure)").grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        self.cat_entry = ctk.CTkEntry(form_frame, width=300)
        self.cat_entry.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkButton(self, text="Add Term", command=self.add_term).pack(pady=10)

        ctk.CTkLabel(
            self,
            text="Tip: Run build_medical_db.py once to create the DB, then use this UI to add more terms.",
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
            messagebox.showerror("DB Missing",
                "Run build_medical_db.py first to create medical_terms.db",
                parent=self)
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
