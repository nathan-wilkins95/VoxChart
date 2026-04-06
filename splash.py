"""
splash.py
Startup splash screen shown while VoxChart loads the Whisper model.
Shows logo text, version, and an animated progress bar.
"""
from __future__ import annotations
import threading
import customtkinter as ctk


class SplashScreen(ctk.CTkToplevel):
    """
    Usage:
        splash = SplashScreen(root)
        splash.set_status("Loading model...")
        splash.set_progress(0.5)
        splash.close()   # call when ready
    """

    def __init__(self, parent, version: str = ""):
        super().__init__(parent)
        self.overrideredirect(True)          # no title bar
        self.attributes("-topmost", True)
        self._version = version
        self._build_ui()
        self._center()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        self.configure(fg_color="#0d0d1a")
        self.geometry("460x260")

        ctk.CTkLabel(
            self, text="VoxChart",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color="#2b7cff"
        ).pack(pady=(40, 2))

        ctk.CTkLabel(
            self,
            text="Offline AI Medical Dictation",
            font=ctk.CTkFont(size=14),
            text_color="#888"
        ).pack(pady=(0, 4))

        if self._version:
            ctk.CTkLabel(
                self, text=f"v{self._version}",
                font=ctk.CTkFont(size=11),
                text_color="#555"
            ).pack(pady=(0, 16))

        self._status_lbl = ctk.CTkLabel(
            self, text="Starting up...",
            font=ctk.CTkFont(size=12),
            text_color="#aaa"
        )
        self._status_lbl.pack(pady=(0, 8))

        self._progress = ctk.CTkProgressBar(self, width=360)
        self._progress.pack(pady=(0, 20))
        self._progress.set(0)

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 460, 260
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def set_status(self, msg: str):
        """Update status label (thread-safe)."""
        self.after(0, lambda m=msg: self._status_lbl.configure(text=m))

    def set_progress(self, value: float):
        """Set progress bar 0.0 – 1.0 (thread-safe)."""
        self.after(0, lambda v=value: self._progress.set(max(0.0, min(1.0, v))))

    def close(self):
        """Destroy the splash and return focus to the parent."""
        self.after(0, self.destroy)
