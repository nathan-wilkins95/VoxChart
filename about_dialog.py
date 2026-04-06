"""
about_dialog.py
VoxChart About window — version, author, GitHub link, credits.
"""
from __future__ import annotations
import webbrowser
import customtkinter as ctk

GITHUB_URL  = "https://github.com/nathan-wilkins95/VoxChart"
LICENSE_URL = "https://github.com/nathan-wilkins95/VoxChart/blob/main/LICENSE"

CREDITS = [
    ("Faster-Whisper",   "https://github.com/guillaumekln/faster-whisper",
     "OpenAI Whisper runtime by Guillaume Klein"),
    ("CustomTkinter",    "https://github.com/TomSchimansky/CustomTkinter",
     "Modern Tkinter UI by Tom Schimansky"),
    ("SoundDevice",      "https://python-sounddevice.readthedocs.io",
     "Audio I/O by Matthias Geier"),
    ("CTranslate2",      "https://github.com/OpenNMT/CTranslate2",
     "Fast inference engine by OpenNMT"),
    ("HuggingFace 🤗",  "https://huggingface.co",
     "Transformers & Datasets (fine-tuning)"),
]


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent, version: str = ""):
        super().__init__(parent)
        self.title("About VoxChart")
        self.geometry("480x500")
        self.resizable(False, False)
        self.grab_set()
        self._version = version
        self._build_ui()

    def _build_ui(self):
        # Header
        ctk.CTkLabel(
            self, text="VoxChart",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#2b7cff"
        ).pack(pady=(28, 2))

        ctk.CTkLabel(
            self,
            text="Offline AI Medical Dictation",
            font=ctk.CTkFont(size=13),
            text_color="#888"
        ).pack(pady=(0, 4))

        if self._version:
            ctk.CTkLabel(
                self, text=f"Version {self._version}",
                font=ctk.CTkFont(size=12, weight="bold")
            ).pack(pady=(0, 2))

        ctk.CTkLabel(
            self,
            text="Copyright \u00a9 2026 Nathan Wilkins",
            font=ctk.CTkFont(size=11),
            text_color="#666"
        ).pack(pady=(0, 16))

        # Buttons row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_row, text="GitHub", width=120,
            command=lambda: webbrowser.open(GITHUB_URL)
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_row, text="MIT License", width=120, fg_color="#333",
            command=lambda: webbrowser.open(LICENSE_URL)
        ).pack(side="left", padx=6)

        # Divider
        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=24, pady=(0, 12))

        # Credits
        ctk.CTkLabel(
            self, text="Third-Party Credits",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(0, 6))

        scroll = ctk.CTkScrollableFrame(self, height=160)
        scroll.pack(fill="x", padx=20, pady=(0, 10))

        for name, url, desc in CREDITS:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkButton(
                row, text=name, anchor="w", fg_color="transparent",
                text_color="#4ea0ff", hover_color="#1a1a2e",
                font=ctk.CTkFont(size=12, underline=True),
                command=lambda u=url: webbrowser.open(u)
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=f"  —  {desc}",
                font=ctk.CTkFont(size=11), text_color="#666"
            ).pack(side="left")

        # Close
        ctk.CTkButton(
            self, text="Close", fg_color="gray", width=100,
            command=lambda: (self.grab_release(), self.destroy())
        ).pack(pady=(0, 20))
