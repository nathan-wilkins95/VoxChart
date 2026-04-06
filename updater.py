"""
updater.py
VoxChart auto-updater.
Checks the latest GitHub release on startup in a background thread.
If a newer version is available, calls on_update_available(version, url, notes).
"""
from __future__ import annotations
import threading
import logging
import urllib.request
import urllib.error
import json
from packaging.version import Version, InvalidVersion

GITHUB_API = "https://api.github.com/repos/nathan-wilkins95/VoxChart/releases/latest"
logger = logging.getLogger("voxchart.updater")


def _fetch_latest() -> dict | None:
    """
    Return release dict with keys: tag, url, notes.
    Returns None on any failure (offline, rate-limit, etc.).
    """
    try:
        req = urllib.request.Request(
            GITHUB_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "VoxChart"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        tag   = data.get("tag_name", "").lstrip("v")
        url   = data.get("html_url", "")
        notes = data.get("body", "") or ""   # release body markdown
        # Trim notes to first 600 chars so the banner isn't a wall of text
        if len(notes) > 600:
            notes = notes[:597] + "..."
        return {"tag": tag, "url": url, "notes": notes}
    except Exception as e:
        logger.debug("Update check failed (offline?): %s", e)
        return None


def check_for_update(
    current_version: str,
    on_update_available,
    on_up_to_date=None,
):
    """
    Runs in a background thread.
    Calls on_update_available(latest_version, release_url, release_notes)
    if a newer version is found.
    Calls on_up_to_date() if already current.
    """
    def _run():
        result = _fetch_latest()
        if not result:
            return
        latest_tag   = result["tag"]
        release_url  = result["url"]
        release_notes = result["notes"]
        try:
            is_newer = Version(latest_tag) > Version(current_version)
        except InvalidVersion:
            logger.warning("Could not parse version: current=%s latest=%s",
                           current_version, latest_tag)
            return
        if is_newer:
            logger.info("Update available: %s -> %s", current_version, latest_tag)
            on_update_available(latest_tag, release_url, release_notes)
        else:
            logger.debug("VoxChart is up to date (%s)", current_version)
            if on_up_to_date:
                on_up_to_date()

    threading.Thread(target=_run, daemon=True, name="voxchart-updater").start()
