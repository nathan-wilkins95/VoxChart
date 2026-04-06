"""
settings.py
VoxChart Settings window.
All settings persist to voxchart_config.json.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

CONFIG_FILE = Path("voxchart_config.json")
logger = logging.getLogger("voxchart.settings")

DEFAULTS = {
    "font_size":        13,
    "autosave_interval": 60,   # seconds; 0 = off
    "default_template": "SOAP Note",
    "model_size":       "large-v3-turbo",
    "language":         "en",
    "theme":            "dark",
    "device":           "cpu",
    "compute_type":     "int8",
    "mic_index":        0,
    "mic_name":         "Default",
    "first_run_complete": True,
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULTS, **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return dict(DEFAULTS)


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    logger.info("Config saved")


class SettingsWindow(ctk.CTkToplevel):
    """
    Opens a settings dialog. Calls on_save(cfg) when the user clicks Save.
    """
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.title("VoxChart Settings")
        self.geometry("480x560")
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save
        self._cfg = load_config()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Settings",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Changes apply after saving.",
                     font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 16))

        form = ctk.CTkScrollableFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        form.columnconfigure(1, weight=1)

        row = 0

        # ---- Appearance ----
        self._section(form, "Appearance", row); row += 1

        self._label(form, "Theme", row)
        self._theme_var = ctk.StringVar(value=self._cfg.get("theme", "dark"))
        ctk.CTkOptionMenu(form, values=["dark", "light", "system"],
                          variable=self._theme_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        self._label(form, "Transcript font size", row)
        self._font_var = ctk.IntVar(value=self._cfg.get("font_size", 13))
        ctk.CTkSlider(form, from_=10, to=20, number_of_steps=10,
                      variable=self._font_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        self._font_lbl = ctk.CTkLabel(form, text=f"{self._font_var.get()}pt", width=40)
        self._font_lbl.grid(row=row-1, column=2, padx=6)
        self._font_var.trace_add("write", lambda *_: self._font_lbl.configure(
            text=f"{self._font_var.get()}pt"))

        # ---- Auto-save ----
        self._section(form, "Auto-save", row); row += 1

        self._label(form, "Auto-save interval", row)
        self._autosave_var = ctk.StringVar(
            value=self._interval_label(self._cfg.get("autosave_interval", 60)))
        ctk.CTkOptionMenu(form, values=["Off", "30 seconds", "60 seconds", "2 minutes", "5 minutes"],
                          variable=self._autosave_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        # ---- Templates ----
        self._section(form, "Templates", row); row += 1

        self._label(form, "Default template", row)
        from templates import all_templates
        tmpl_names = list(all_templates().keys())
        self._tmpl_var = ctk.StringVar(value=self._cfg.get("default_template", "SOAP Note"))
        ctk.CTkOptionMenu(form, values=tmpl_names,
                          variable=self._tmpl_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        # ---- AI Model ----
        self._section(form, "AI Model", row); row += 1

        self._label(form, "Whisper model size", row)
        self._model_var = ctk.StringVar(value=self._cfg.get("model_size", "large-v3-turbo"))
        ctk.CTkOptionMenu(form,
                          values=["tiny", "tiny.en", "base", "base.en",
                                  "small", "small.en", "medium", "medium.en",
                                  "large-v2", "large-v3", "large-v3-turbo"],
                          variable=self._model_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        self._label(form, "Language", row)
        self._lang_var = ctk.StringVar(value=self._cfg.get("language", "en"))
        ctk.CTkOptionMenu(form,
                          values=["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ar"],
                          variable=self._lang_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        self._label(form, "Compute device", row)
        self._device_var = ctk.StringVar(value=self._cfg.get("device", "cpu"))
        ctk.CTkOptionMenu(form, values=["cuda", "cpu"],
                          variable=self._device_var).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        # ---- Buttons ----
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(btn_row, text="Cancel", fg_color="gray", width=100,
                      command=lambda: (self.grab_release(), self.destroy())).pack(side="left")
        ctk.CTkButton(btn_row, text="Save Settings", width=160,
                      command=self._save).pack(side="right")

    def _section(self, parent, text, row):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#2b7cff").grid(row=row, column=0, columnspan=3,
                                                sticky="w", pady=(14, 2))

    def _label(self, parent, text, row):
        ctk.CTkLabel(parent, text=text, anchor="w", width=180).grid(
            row=row, column=0, sticky="w", pady=4)

    def _interval_label(self, seconds: int) -> str:
        return {0: "Off", 30: "30 seconds", 60: "60 seconds",
                120: "2 minutes", 300: "5 minutes"}.get(seconds, "60 seconds")

    def _interval_seconds(self, label: str) -> int:
        return {"Off": 0, "30 seconds": 30, "60 seconds": 60,
                "2 minutes": 120, "5 minutes": 300}.get(label, 60)

    def _save(self):
        self._cfg["theme"]            = self._theme_var.get()
        self._cfg["font_size"]        = int(self._font_var.get())
        self._cfg["autosave_interval"] = self._interval_seconds(self._autosave_var.get())
        self._cfg["default_template"] = self._tmpl_var.get()
        self._cfg["model_size"]       = self._model_var.get()
        self._cfg["language"]         = self._lang_var.get()
        self._cfg["device"]           = self._device_var.get()
        self._cfg["compute_type"]     = "float16" if self._device_var.get() == "cuda" else "int8"
        save_config(self._cfg)
        ctk.set_appearance_mode(self._cfg["theme"])
        messagebox.showinfo("Saved", "Settings saved! Restart the app for model/device changes.")
        if self._on_save:
            self._on_save(self._cfg)
        self.grab_release()
        self.destroy()
