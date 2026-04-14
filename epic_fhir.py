"""epic_fhir.py

SMART on FHIR integration for VoxChart.

Supports
--------
* OAuth2 PKCE + Standalone Launch against Epic's SMART endpoint
* Patient / Encounter context read (read-only)
* DocumentReference write (posts the chart note back to Epic)
* Local credential + token cache in epic_fhir_config.json
* Background token-refresh thread

Setup
-----
1.  Register at https://open.epic.com → "Build Apps" → create a Non-Production app.
2.  Set redirect URI to:  http://localhost:8765/callback
3.  Request scopes:  launch patient/Patient.read patient/Encounter.read
                     patient/DocumentReference.write openid fhirUser
4.  Copy your Client ID into epic_fhir_config.json (see CREDENTIAL_FILE below).
5.  For Production, repeat with a Production app and update the FHIR base URL.

Usage (standalone test)
-----------------------
    python epic_fhir.py

Usage (from app.py)
-------------------
    from epic_fhir import EpicFHIRClient, FHIRNotConfiguredError
    client = EpicFHIRClient()
    if client.is_configured():
        client.launch_auth()   # opens browser, spins local callback server
        patient = client.get_patient()
        client.write_note(formatted_text, patient_id=patient["id"])

Dependencies
------------
    pip install requests
    (authlib is optional — we roll our own PKCE to avoid extra deps)

Notes
-----
* This module never stores PHI on disk.  The token cache stores OAuth tokens only.
* Epic Sandbox FHIR base URL:  https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
* Epic requires TLS 1.2+ for all API calls — requests handles this automatically.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import logging
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

logger = logging.getLogger("voxchart.epic_fhir")

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────

CREDENTIAL_FILE = Path("epic_fhir_config.json")
TOKEN_CACHE     = Path("epic_exports") / ".fhir_token_cache.json"

DEFAULT_CONFIG = {
    "client_id":       "",           # ← paste your Epic app Client ID here
    "fhir_base_url":   "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
    "auth_url":        "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
    "token_url":       "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
    "redirect_uri":    "http://localhost:8765/callback",
    "scopes":          "launch patient/Patient.read patient/Encounter.read patient/DocumentReference.write openid fhirUser",
    "use_sandbox":     True,
}


# ─────────────────────────────────────────────────────────────────────────────
#  Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class FHIRNotConfiguredError(Exception):
    """Raised when client_id is missing from the config file."""

class FHIRAuthError(Exception):
    """Raised when OAuth2 authorization fails."""

class FHIRRequestError(Exception):
    """Raised when a FHIR API call fails."""


# ─────────────────────────────────────────────────────────────────────────────
#  PKCE helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pkce_verifier(length: int = 64) -> str:
    return base64.urlsafe_b64encode(os.urandom(length)).rstrip(b"=").decode()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


# ─────────────────────────────────────────────────────────────────────────────
#  Local OAuth callback server (single-use)
# ─────────────────────────────────────────────────────────────────────────────

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler that captures the OAuth ?code=... callback."""

    def log_message(self, fmt, *args):  # suppress default access logs
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if "error" in params:
            self.server.auth_result = {"error": params["error"],
                                        "error_description": params.get("error_description", "")}
        else:
            self.server.auth_result = {"code": params.get("code", ""),
                                        "state": params.get("state", "")}

        body = (
            b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            b"<h2>VoxChart</h2>"
            b"<p>Authorization complete! You may close this window and return to VoxChart.</p>"
            b"</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _run_callback_server(port: int = 8765, timeout: int = 120) -> dict:
    """Spin up a temporary server, block until a callback is received or timeout."""
    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.auth_result = {}
    server.timeout = timeout
    server.handle_request()  # blocks until one request arrives or timeout
    return server.auth_result


# ─────────────────────────────────────────────────────────────────────────────
#  Main client
# ─────────────────────────────────────────────────────────────────────────────

class EpicFHIRClient:
    """
    SMART on FHIR client for Epic.

    Thread-safe token management; supports both sandbox and production endpoints.
    """

    def __init__(self, config_path: Path = CREDENTIAL_FILE):
        self._cfg = self._load_config(config_path)
        self._access_token:  Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._patient_id:    Optional[str] = None
        self._encounter_id:  Optional[str] = None
        self._lock = threading.Lock()
        self._load_token_cache()

    # ── Config ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
            logger.info("Created Epic FHIR config at %s", path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Fill missing keys with defaults
        for k, v in DEFAULT_CONFIG.items():
            raw.setdefault(k, v)
        return raw

    def save_config(self) -> None:
        CREDENTIAL_FILE.write_text(json.dumps(self._cfg, indent=2), encoding="utf-8")

    def is_configured(self) -> bool:
        """Return True if a client_id has been set."""
        return bool(self._cfg.get("client_id"))

    def is_authenticated(self) -> bool:
        """Return True if we hold a valid (non-expired) access token."""
        with self._lock:
            if not self._access_token:
                return False
            if self._token_expires and datetime.now() >= self._token_expires:
                return False
            return True

    def get_config(self) -> dict:
        return dict(self._cfg)

    def set_config(self, **kwargs) -> None:
        self._cfg.update(kwargs)
        self.save_config()

    # ── Token cache ──────────────────────────────────────────────────────────

    def _load_token_cache(self) -> None:
        if not TOKEN_CACHE.exists():
            return
        try:
            data = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
            self._access_token  = data.get("access_token")
            self._refresh_token = data.get("refresh_token")
            exp = data.get("expires_at")
            if exp:
                self._token_expires = datetime.fromisoformat(exp)
            logger.info("Loaded cached FHIR token")
        except Exception as e:
            logger.warning("Could not load FHIR token cache: %s", e)

    def _save_token_cache(self) -> None:
        Path("epic_exports").mkdir(parents=True, exist_ok=True)
        data = {
            "access_token":  self._access_token,
            "refresh_token": self._refresh_token,
            "expires_at":    self._token_expires.isoformat() if self._token_expires else None,
        }
        TOKEN_CACHE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def clear_auth(self) -> None:
        """Revoke the cached tokens (logout)."""
        with self._lock:
            self._access_token  = None
            self._refresh_token = None
            self._token_expires = None
            self._patient_id    = None
            self._encounter_id  = None
        if TOKEN_CACHE.exists():
            TOKEN_CACHE.unlink()
        logger.info("FHIR auth cleared")

    # ── OAuth2 PKCE Launch ───────────────────────────────────────────────────

    def launch_auth(
        self,
        on_success: Optional[Callable[[], None]] = None,
        on_error:   Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Begin SMART on FHIR Standalone Launch in a background thread.
        Opens the system browser for Epic login, then exchanges the
        authorization code for tokens via a local callback server.

        Callbacks fire on the background thread; marshal to the UI thread
        via `widget.after(0, ...)` if needed.
        """
        if not _HAS_REQUESTS:
            msg = "'requests' package not installed.  Run: pip install requests"
            logger.error(msg)
            if on_error:
                on_error(msg)
            return

        if not self.is_configured():
            msg = "Epic FHIR client_id not set. Open Settings → Epic FHIR."
            logger.error(msg)
            if on_error:
                on_error(msg)
            return

        def _auth_flow():
            try:
                verifier   = _pkce_verifier()
                challenge  = _pkce_challenge(verifier)
                state      = secrets.token_urlsafe(16)

                params = {
                    "response_type":         "code",
                    "client_id":             self._cfg["client_id"],
                    "redirect_uri":          self._cfg["redirect_uri"],
                    "scope":                 self._cfg["scopes"],
                    "state":                 state,
                    "code_challenge":        challenge,
                    "code_challenge_method": "S256",
                    "aud":                   self._cfg["fhir_base_url"],
                }
                auth_url = self._cfg["auth_url"] + "?" + urllib.parse.urlencode(params)
                logger.info("Opening Epic auth URL")
                webbrowser.open(auth_url)

                result = _run_callback_server(timeout=120)

                if "error" in result:
                    raise FHIRAuthError(result.get("error_description") or result["error"])
                if result.get("state") != state:
                    raise FHIRAuthError("OAuth state mismatch — possible CSRF")

                code = result["code"]
                token_resp = requests.post(
                    self._cfg["token_url"],
                    data={
                        "grant_type":    "authorization_code",
                        "code":           code,
                        "redirect_uri":   self._cfg["redirect_uri"],
                        "client_id":      self._cfg["client_id"],
                        "code_verifier":  verifier,
                    },
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
                token_resp.raise_for_status()
                tokens = token_resp.json()

                with self._lock:
                    self._access_token  = tokens["access_token"]
                    self._refresh_token = tokens.get("refresh_token")
                    expires_in = tokens.get("expires_in", 3600)
                    self._token_expires = datetime.now() + timedelta(seconds=expires_in - 30)
                    # Epic embeds patient / encounter context in the token response
                    self._patient_id    = tokens.get("patient")
                    self._encounter_id  = tokens.get("encounter")

                self._save_token_cache()
                logger.info("Epic FHIR auth successful; patient=%s", self._patient_id)

                if on_success:
                    on_success()

            except Exception as exc:
                logger.error("Epic FHIR auth failed: %s", exc)
                if on_error:
                    on_error(str(exc))

        threading.Thread(target=_auth_flow, daemon=True).start()

    def refresh_token_if_needed(self) -> bool:
        """Attempt a silent token refresh.  Returns True if refresh succeeded."""
        if not self._refresh_token:
            return False
        try:
            resp = requests.post(
                self._cfg["token_url"],
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id":     self._cfg["client_id"],
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            tokens = resp.json()
            with self._lock:
                self._access_token  = tokens["access_token"]
                self._refresh_token = tokens.get("refresh_token", self._refresh_token)
                self._token_expires = datetime.now() + timedelta(
                    seconds=tokens.get("expires_in", 3600) - 30
                )
            self._save_token_cache()
            logger.info("FHIR token refreshed silently")
            return True
        except Exception as e:
            logger.warning("Token refresh failed: %s", e)
            return False

    # ── FHIR requests ────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept":        "application/fhir+json",
            "Content-Type":  "application/fhir+json",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        if not self.is_authenticated():
            if not self.refresh_token_if_needed():
                raise FHIRAuthError("Not authenticated.  Call launch_auth() first.")
        url = self._cfg["fhir_base_url"].rstrip("/") + "/" + path.lstrip("/")
        resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
        if resp.status_code == 401:
            if self.refresh_token_if_needed():
                resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> Any:
        if not self.is_authenticated():
            if not self.refresh_token_if_needed():
                raise FHIRAuthError("Not authenticated.  Call launch_auth() first.")
        url = self._cfg["fhir_base_url"].rstrip("/") + "/" + path.lstrip("/")
        resp = requests.post(url, headers=self._headers(), json=body, timeout=30)
        if resp.status_code == 401:
            if self.refresh_token_if_needed():
                resp = requests.post(url, headers=self._headers(), json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ── Clinical resource methods ────────────────────────────────────────────

    def get_patient(self, patient_id: Optional[str] = None) -> dict:
        """
        Fetch Patient resource.  Uses the patient ID from the launch context
        if patient_id is not supplied.
        """
        pid = patient_id or self._patient_id
        if not pid:
            raise FHIRRequestError("No patient ID available.  Launch from an Epic context.")
        return self._get(f"Patient/{pid}")

    def get_patient_name(self, patient: Optional[dict] = None) -> str:
        """Extract a readable name string from a Patient resource."""
        if patient is None:
            patient = self.get_patient()
        names = patient.get("name", [])
        if not names:
            return ""
        n = names[0]
        family = n.get("family", "")
        given  = " ".join(n.get("given", []))
        return f"{given} {family}".strip()

    def get_patient_mrn(self, patient: Optional[dict] = None) -> str:
        """Extract MRN from Patient identifier list."""
        if patient is None:
            patient = self.get_patient()
        for ident in patient.get("identifier", []):
            if "MR" in ident.get("type", {}).get("coding", [{}])[0].get("code", ""):
                return ident.get("value", "")
        # fallback: first identifier
        ids = patient.get("identifier", [])
        return ids[0].get("value", "") if ids else ""

    def get_encounter(self, encounter_id: Optional[str] = None) -> dict:
        """Fetch Encounter resource."""
        eid = encounter_id or self._encounter_id
        if not eid:
            raise FHIRRequestError("No encounter ID available.")
        return self._get(f"Encounter/{eid}")

    def get_encounter_type(self, encounter: Optional[dict] = None) -> str:
        """Extract human-readable encounter type."""
        if encounter is None:
            encounter = self.get_encounter()
        types = encounter.get("type", [])
        if not types:
            return ""
        codings = types[0].get("coding", [])
        if codings:
            return codings[0].get("display", "")
        return types[0].get("text", "")

    def write_note(
        self,
        note_text: str,
        patient_id:   Optional[str] = None,
        encounter_id: Optional[str] = None,
        provider_name: str = "",
        note_type_code: str = "11506-3",   # LOINC: Progress note
        note_type_display: str = "Progress note",
    ) -> dict:
        """
        Write a clinical note back to Epic as a FHIR DocumentReference.

        Parameters
        ----------
        note_text          : Plain-text note content.
        patient_id         : FHIR Patient ID (uses launch context if omitted).
        encounter_id       : FHIR Encounter ID (uses launch context if omitted).
        provider_name      : Free-text author name (optional).
        note_type_code     : LOINC code. Default 11506-3 = Progress note.
                             Common alternatives:
                             11488-4  Consultation note
                             18842-5  Discharge summary
                             34117-2  History and physical note
                             34109-9  Evaluation and management note
        note_type_display  : Human-readable label for note_type_code.

        Returns
        -------
        The created DocumentReference resource as a dict.
        """
        pid = patient_id or self._patient_id
        eid = encounter_id or self._encounter_id

        if not pid:
            raise FHIRRequestError("Patient ID required to write a note.")

        # Base64-encode the note content as required by FHIR Attachment
        content_b64 = base64.b64encode(note_text.encode("utf-8")).decode("utf-8")
        now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        doc_ref: dict = {
            "resourceType": "DocumentReference",
            "status":       "current",
            "docStatus":    "final",
            "type": {
                "coding": [{
                    "system":  "http://loinc.org",
                    "code":    note_type_code,
                    "display": note_type_display,
                }]
            },
            "subject": {"reference": f"Patient/{pid}"},
            "date":    now_iso,
            "content": [{
                "attachment": {
                    "contentType": "text/plain",
                    "data":        content_b64,
                    "title":       f"VoxChart Note — {now_iso[:10]}",
                }
            }],
        }

        if eid:
            doc_ref["context"] = {"encounter": [{"reference": f"Encounter/{eid}"}]}

        if provider_name:
            doc_ref["author"] = [{"display": provider_name}]

        logger.info("Writing DocumentReference for patient %s", pid)
        result = self._post("DocumentReference", doc_ref)
        logger.info("DocumentReference created: %s", result.get("id"))
        return result

    # ── Context accessors ────────────────────────────────────────────────────

    @property
    def patient_id(self) -> Optional[str]:
        return self._patient_id

    @property
    def encounter_id(self) -> Optional[str]:
        return self._encounter_id


# ─────────────────────────────────────────────────────────────────────────────
#  Module-level singleton (shared across the app)
# ─────────────────────────────────────────────────────────────────────────────

_client: Optional[EpicFHIRClient] = None


def get_client() -> EpicFHIRClient:
    global _client
    if _client is None:
        _client = EpicFHIRClient()
    return _client


# ─────────────────────────────────────────────────────────────────────────────
#  CLI smoke test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = get_client()

    if not client.is_configured():
        print("\n⚠️  Epic FHIR not configured.")
        print(f"Edit {CREDENTIAL_FILE} and set your client_id, then re-run.")
    else:
        print(f"Client ID: {client.get_config()['client_id']}")
        print("Launching Epic SMART auth flow — check your browser...")
        done = threading.Event()
        client.launch_auth(
            on_success=lambda: (print("✅ Authenticated!"), done.set()),
            on_error=lambda e: (print(f"❌ Error: {e}"), done.set()),
        )
        done.wait(timeout=130)
