"""Read and manage the AI triage JSON cache written by Copilot sessions."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ado_dashboard import config
from ado_dashboard.investigation_prompts import board_key_from_url
from ado_dashboard.models import TriageAnalysis

log = logging.getLogger(__name__)


def cache_path(board_url: str) -> Path:
    """Return the cache file path for a board, ensuring the directory exists."""
    key = board_key_from_url(board_url)
    cache_dir = Path(config.TRIAGE_CACHE_DIR).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"


def read_cached_triage(board_url: str) -> TriageAnalysis | None:
    """Read and parse cached AI triage results for a board.

    Returns None if the file doesn't exist, is corrupt, or is being written.
    """
    path = cache_path(board_url)
    if not path.is_file():
        return None

    try:
        content = path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        log.warning("Failed to read triage cache %s: %s", path, exc)
        return None

    if not content:
        return None

    # Partial-write protection: ensure file looks complete
    if not content.endswith("}"):
        log.debug("Triage cache %s appears truncated, skipping", path)
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        log.warning("Invalid JSON in triage cache %s: %s", path, exc)
        return None

    if not isinstance(data, dict) or "items" not in data:
        log.warning("Triage cache %s missing 'items' key", path)
        return None

    try:
        return TriageAnalysis.from_json(data)
    except Exception as exc:
        log.warning("Failed to parse triage cache %s: %s", path, exc)
        return None


def is_cache_fresh(board_url: str, max_age: int | None = None) -> bool:
    """Return True if the cache file exists and is younger than max_age seconds."""
    if max_age is None:
        max_age = config.TRIAGE_CACHE_MAX_AGE_SECONDS
    path = cache_path(board_url)
    if not path.is_file():
        return False
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) < max_age
    except OSError:
        return False


def is_cache_newer_than(board_url: str, threshold: float) -> bool:
    """Return True if the cache file exists and was modified after threshold (epoch)."""
    path = cache_path(board_url)
    if not path.is_file():
        return False
    try:
        return path.stat().st_mtime > threshold
    except OSError:
        return False


def cache_age_str(board_url: str) -> str:
    """Human-readable age of the cache file, e.g. '5m', '1h', or '?' if missing."""
    path = cache_path(board_url)
    if not path.is_file():
        return "?"
    try:
        age_secs = time.time() - path.stat().st_mtime
        if age_secs < 60:
            return f"{int(age_secs)}s"
        if age_secs < 3600:
            return f"{int(age_secs / 60)}m"
        return f"{int(age_secs / 3600)}h"
    except OSError:
        return "?"


def invalidate_cache(board_url: str) -> None:
    """Delete the cache file for a board, if it exists."""
    path = cache_path(board_url)
    try:
        path.unlink(missing_ok=True)
        log.info("Invalidated triage cache: %s", path)
    except OSError as exc:
        log.warning("Failed to delete triage cache %s: %s", path, exc)
