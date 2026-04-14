"""epic_integration_dialog.py

EpicIntegrationDialog — replaces the old EpicExportDialog in app.py.

Two tabs:
  • Clipboard Export  — always works, no Epic credentials needed
  • Send to Epic FHIR — uses epic_fhir.EpicFHIRClient; disabled with a clear
                        message when no client_id is configured

Usage (from app.py):
    from epic_integration_dialog import EpicIntegrationDialog
    from epic_fhir import get_client
    EpicIntegrationDialog(parent, transcript="...", fhir_client=get_client())
"""

from __future__ import annotations

import threading
from tkinter import messagebox
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from epic_exporter import (
    format_for_epic,
    copy_to_clipboard,
    export_to_file,
    append_audit_log,
    NOTE_TYPE_LOINC,
    NoteModel,
)


class EpicIntegrationDialog(ctk.CTkToplevel):
    """
    Epic integration dialog with Clipboard and FHIR Send tabs.

    Parameters
    ----------
    parent        : Parent tkinter widget.
    transcript    : Raw dictated transcript string.
    fhir_client   : An EpicFHIRClient instance (or None to disable FHIR tab).
    provider_name : Pre-fill provider name from app settings (optional).
    """

    def __init__(
        self,
        parent,
        transcript:    str = "",
        fhir_client=None,
        provider_name: str = "",
    ):
        super().__init__(parent)
        self.title("Epic Integration")
        self.geometry("540x600")
        self.resizable(False, False)
        self.grab_set()

        self.transcript    = transcript
        self.fhir_client   = fhir_client
        self._note: Optional[NoteModel] = None

        # ── Header ───────────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Epic Integration",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Choose how to send this note to Epic.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(pady=(0, 10))

        # ── Shared patient-info form ─────────────────────────────────────────────────────
        self._build_patient_form(provider_name)

        # ── Tabs ──────────────────────────────────────────────────────────────────────
        self._tabview = ctk.CTkTabview(self, height=260)
        self._tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._tabview.add("📋 Clipboard")
        self._tabview.add("⚡ Send to Epic")

        self._build_clipboard_tab(self._tabview.tab("📋 Clipboard"))
        self._build_fhir_tab(self._tabview.tab("⚡ Send to Epic"))

        # ── Cancel button ────────────────────────────────────────────────────────────────
        ctk.CTkButton(
            self,
            text="Cancel",
            fg_color="gray",
            width=100,
            command=self._close,
        ).pack(pady=(0, 16))

    # ── Patient-info form ────────────────────────────────────────────────────────────────

    def _build_patient_form(self, default_provider: str = ""):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkLabel(
            frame,
            text="Patient Info  (optional — fills note header)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))

        fields = [
            ("Provider Name", "e.g., Dr. Smith",  default_provider),
            ("Patient Name",  "e.g., John Doe",   ""),
            ("Date of Birth", "e.g., 01/15/1970", ""),
            ("MRN",           "e.g., 123456",      ""),
        ]
        self._entries: dict[str, ctk.CTkEntry] = {}
        for row_idx, (label, ph, default) in enumerate(fields, start=1):
            ctk.CTkLabel(frame, text=label, width=130, anchor="w").grid(
                row=row_idx, column=0, padx=(10, 6), pady=4, sticky="w")
            e = ctk.CTkEntry(frame, width=280, placeholder_text=ph)
            if default:
                e.insert(0, default)
            e.grid(row=row_idx, column=1, pady=4, padx=(0, 10))
            self._entries[label] = e

        ctk.CTkLabel(frame, text="Note Type", width=130, anchor="w").grid(
            row=len(fields)+1, column=0, padx=(10, 6), pady=4, sticky="w")
        self._note_type_var = ctk.StringVar(value="Progress note")
        ctk.CTkOptionMenu(
            frame,
            variable=self._note_type_var,
            values=list(NOTE_TYPE_LOINC.keys()),
            width=280,
        ).grid(row=len(fields)+1, column=1, pady=4, padx=(0, 10))

    def _get_note(self) -> NoteModel:
        self._note = format_for_epic(
            self.transcript,
            provider_name = self._entries["Provider Name"].get().strip(),
            patient_name  = self._entries["Patient Name"].get().strip(),
            dob           = self._entries["Date of Birth"].get().strip(),
            mrn           = self._entries["MRN"].get().strip(),
            note_type     = self._note_type_var.get(),
        )
        return self._note

    # ── Clipboard tab ─────────────────────────────────────────────────────────────────

    def _build_clipboard_tab(self, parent):
        ctk.CTkLabel(
            parent,
            text="Copy the formatted note to your clipboard.\n"
                 "Then switch to Epic, open a note field, and press Ctrl+V.",
            font=ctk.CTkFont(size=12),
            justify="center",
            text_color="gray",
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            parent,
            text="Works with any Epic version — no credentials required.",
            font=ctk.CTkFont(size=11),
            text_color="#5a9e6a",
        ).pack(pady=(0, 16))

        ctk.CTkButton(
            parent,
            text="Copy Plain Text  (Ctrl+V into Epic)",
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1a6b3c",
            hover_color="#23994f",
            command=self._do_clipboard_plain,
        ).pack(pady=6, padx=20, fill="x")

        ctk.CTkButton(
            parent,
            text="Copy SmartPhrase Version",
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color="#2b4a7c",
            hover_color="#3a6aae",
            command=self._do_clipboard_smartphrase,
        ).pack(pady=4, padx=20, fill="x")

        ctk.CTkLabel(
            parent,
            text="SmartPhrase: type  .VOXNOTE.  in Epic to expand",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        ).pack(pady=(2, 0))

    def _do_clipboard_plain(self):
        note  = self._get_note()
        saved = export_to_file(note)
        copy_to_clipboard(note.plain_text())
        append_audit_log(note, method="clipboard", status="ok")
        self._close()
        messagebox.showinfo(
            "Copied!",
            f"Note copied to clipboard!\n\n"
            f"1. Open Epic\n2. Open your note field\n3. Ctrl+V\n\n"
            f"Saved to:\n{saved}",
        )

    def _do_clipboard_smartphrase(self):
        note = self._get_note()
        export_to_file(note, smart_phrase=True)
        copy_to_clipboard(note.smart_phrase_text())
        append_audit_log(note, method="clipboard_smartphrase", status="ok")
        self._close()
        messagebox.showinfo(
            "SmartPhrase Copied!",
            "SmartPhrase note copied to clipboard.\n\n"
            "Paste into Epic, then type  .VOXNOTE.  to expand sections.",
        )

    # ── FHIR Send tab ──────────────────────────────────────────────────────────────────

    def _build_fhir_tab(self, parent):
        client = self.fhir_client

        if client is None or not client.is_configured():
            ctk.CTkLabel(
                parent,
                text="Epic FHIR Not Configured",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="orange",
            ).pack(pady=(24, 8))
            ctk.CTkLabel(
                parent,
                text=(
                    "To enable direct FHIR note writing:\n\n"
                    "1. Register at  fhir.epic.com → Build Apps\n"
                    "2. Application Audience: Clinicians or Admin Users\n"
                    "3. Set redirect URI:  http://localhost:8765/callback\n"
                    "4. Add Incoming APIs: Patient.Read, Encounter.Read,\n"
                    "   DocumentReference.Read, DocumentReference.Write\n"
                    "5. Paste your Non-Production Client ID into:\n"
                    "   epic_fhir_config.json  →  client_id"
                ),
                font=ctk.CTkFont(size=11),
                text_color="gray",
                justify="left",
            ).pack(pady=(0, 8), padx=20)
            return

        self._fhir_status_lbl = ctk.CTkLabel(
            parent,
            text=self._fhir_status_text(),
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left",
        )
        self._fhir_status_lbl.pack(pady=(16, 4), padx=20, anchor="w")

        self._patient_ctx_lbl = ctk.CTkLabel(
            parent,
            text="Patient context: not loaded",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self._patient_ctx_lbl.pack(pady=(0, 12), padx=20, anchor="w")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=4)

        if not client.is_authenticated():
            self._auth_btn = ctk.CTkButton(
                btn_row,
                text="Connect to Epic (Login)",
                height=42,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#2b4a7c",
                hover_color="#3a6aae",
                command=self._do_fhir_auth,
            )
            self._auth_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._send_btn = ctk.CTkButton(
            btn_row,
            text="Send Note to Epic (FHIR)",
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1a6b3c",
            hover_color="#23994f",
            state="normal" if client.is_authenticated() else "disabled",
            command=self._do_fhir_send,
        )
        self._send_btn.pack(side="left", fill="x", expand=True)

        self._fhir_progress = ctk.CTkLabel(
            parent, text="", font=ctk.CTkFont(size=11), text_color="gray",
        )
        self._fhir_progress.pack(pady=(8, 0), padx=20)

        if client.is_authenticated():
            self.after(200, self._load_patient_context)

    def _fhir_status_text(self) -> str:
        if self.fhir_client is None:
            return "FHIR: not available"
        env  = "Sandbox" if self.fhir_client.get_config().get("use_sandbox") else "Production"
        auth = "✅ Authenticated" if self.fhir_client.is_authenticated() else "🔒 Not logged in"
        return f"Environment: {env}   |   {auth}"

    def _do_fhir_auth(self):
        if not hasattr(self, "_auth_btn"):
            return
        self._auth_btn.configure(state="disabled", text="Opening browser...")
        self._fhir_progress.configure(text="Waiting for Epic login in browser...", text_color="gray")

        def on_success():
            self.after(0, self._on_fhir_auth_success)

        def on_error(msg):
            self.after(0, lambda m=msg: self._on_fhir_auth_error(m))

        self.fhir_client.launch_auth(on_success=on_success, on_error=on_error)

    def _on_fhir_auth_success(self):
        if hasattr(self, "_auth_btn"):
            self._auth_btn.configure(state="disabled", text="Connected ✓", fg_color="#2a5a2a")
        self._send_btn.configure(state="normal")
        self._fhir_status_lbl.configure(text=self._fhir_status_text(), text_color="#5a9e6a")
        self._fhir_progress.configure(text="✅ Login successful — ready to send.", text_color="#5a9e6a")
        self._load_patient_context()

    def _on_fhir_auth_error(self, msg: str):
        if hasattr(self, "_auth_btn"):
            self._auth_btn.configure(state="normal", text="Connect to Epic (Login)")
        self._fhir_progress.configure(text=f"❌ Auth failed: {msg}", text_color="red")

    def _load_patient_context(self):
        client = self.fhir_client
        if client is None or not client.is_authenticated():
            return

        def _fetch():
            try:
                patient = client.get_patient()
                name    = client.get_patient_name(patient)
                mrn     = client.get_patient_mrn(patient)
                encounter_type = ""
                try:
                    enc = client.get_encounter()
                    encounter_type = client.get_encounter_type(enc)
                except Exception:
                    pass
                self.after(0, lambda: self._apply_patient_context(name, mrn, encounter_type))
            except Exception as e:
                self.after(0, lambda err=e: self._patient_ctx_lbl.configure(
                    text=f"Could not load patient context: {err}", text_color="orange"
                ))

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_patient_context(self, name: str, mrn: str, encounter_type: str):
        if name:
            self._entries["Patient Name"].delete(0, "end")
            self._entries["Patient Name"].insert(0, name)
        if mrn:
            self._entries["MRN"].delete(0, "end")
            self._entries["MRN"].insert(0, mrn)
        ctx_parts = [f"Patient: {name}"]
        if mrn:
            ctx_parts.append(f"MRN: {mrn}")
        if encounter_type:
            ctx_parts.append(f"Visit: {encounter_type}")
        self._patient_ctx_lbl.configure(
            text="  ".join(ctx_parts), text_color="#5a9e6a"
        )

    def _do_fhir_send(self):
        if self.fhir_client is None or not self.fhir_client.is_authenticated():
            messagebox.showwarning("Not Authenticated", "Connect to Epic first.")
            return

        note = self._get_note()
        self._send_btn.configure(state="disabled", text="Sending...")
        self._fhir_progress.configure(text="Posting DocumentReference to Epic...", text_color="gray")

        client = self.fhir_client

        def _send():
            try:
                result      = client.write_note(
                    note_text          = note.plain_text(),
                    provider_name      = note.provider_name,
                    note_type_code     = note.loinc_code(),
                    note_type_display  = note.loinc_display(),
                )
                resource_id = result.get("id", "")
                export_to_file(note)
                append_audit_log(note, method="fhir", fhir_resource_id=resource_id, status="ok")
                self.after(0, lambda: self._on_fhir_send_success(resource_id))
            except Exception as exc:
                err = str(exc)
                append_audit_log(note, method="fhir", status="error", error_msg=err)
                self.after(0, lambda e=err: self._on_fhir_send_error(e))

        threading.Thread(target=_send, daemon=True).start()

    def _on_fhir_send_success(self, resource_id: str):
        self._send_btn.configure(state="normal", text="Send Note to Epic (FHIR)")
        self._fhir_progress.configure(
            text=f"✅ Note filed in Epic  (ID: {resource_id or 'received'})",
            text_color="#5a9e6a",
        )
        self._close()
        messagebox.showinfo(
            "Note Sent to Epic!",
            f"Your chart note was successfully written to Epic.\n\n"
            f"FHIR DocumentReference ID: {resource_id or 'N/A'}\n\n"
            f"The note also appears in your local epic_exports/ folder.",
        )

    def _on_fhir_send_error(self, msg: str):
        self._send_btn.configure(state="normal", text="Send Note to Epic (FHIR)")
        self._fhir_progress.configure(text=f"❌ Send failed: {msg}", text_color="red")
        messagebox.showerror(
            "FHIR Send Failed",
            f"Could not write note to Epic:\n\n{msg}\n\n"
            f"Tip: Use  📋 Clipboard  tab as a fallback.",
        )

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
