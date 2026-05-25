"""Async client that runs the Get-TriageItems.ps1 script and returns TriageItem models."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from urllib.parse import unquote

from wip_dashboard import config
from wip_dashboard.models import TriageItem

log = logging.getLogger(__name__)

# Bundled example script path — for documentation only; not auto-executed.
_BUNDLED_EXAMPLE = Path(__file__).resolve().parent / "scripts" / "Get-TriageItems.ps1.example"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class TriageClientError(Exception):
    """Raised when the triage PowerShell script fails."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_script_path() -> Path:
    """Return the triage script path from config.

    Raises :class:`TriageClientError` when no path is configured or the path
    does not exist.
    """
    if not config.TRIAGE_SCRIPT_PATH:
        raise TriageClientError(
            "triage_script_path is not configured — copy "
            f"`{_BUNDLED_EXAMPLE.name}`, fill in your area path, and set "
            "`triage_script_path` in your config (Settings screen or config.json). "
            "See docs/triage-and-investigation.md for details."
        )

    script_path = Path(config.TRIAGE_SCRIPT_PATH)
    if not script_path.exists():
        raise TriageClientError(
            f"Triage script not found at configured path {script_path}. "
            "Remove the override or fix the path in Settings."
        )
    return script_path


def _find_powershell() -> str:
    """Locate pwsh or powershell on PATH, raising if neither is found."""
    ps = shutil.which("pwsh") or shutil.which("powershell")
    if ps is None:
        raise TriageClientError(
            "Neither 'pwsh' nor 'powershell' found on PATH. "
            "Install PowerShell 7+ from https://aka.ms/powershell and restart your shell."
        )
    return ps


def _extract_team_from_url(url: str) -> str | None:
    """Extract the team name from an ADO board URL.

    Expected format: https://dev.azure.com/{org}/{project}/_boards/board/t/{team}/...
    Returns the URL-decoded team name, or None if the URL doesn't match.
    """
    try:
        marker = "/_boards/board/t/"
        idx = url.index(marker)
        rest = url[idx + len(marker) :]
        team = rest.split("/")[0]
        return unquote(team)
    except (ValueError, IndexError):
        return None


def _extract_json_array(raw: str) -> list[dict]:
    """Extract the last JSON array from *raw* stdout.

    The PowerShell script may emit non-JSON status lines before or after the
    JSON payload.  We try ``json.loads`` on the whole string first, then
    progressively try substrings from each ``[`` to the last ``]``, working
    backwards so we prefer the largest valid array.  This is immune to
    brackets inside JSON string values because ``json.loads`` handles escaping.
    """
    stripped = raw.strip()

    # Fast path: entire output is valid JSON
    try:
        result = json.loads(stripped)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Find the last ']' in the output
    end = stripped.rfind("]")
    if end == -1:
        raise TriageClientError(
            f"No JSON array found in script output.\nRaw output: {raw[:500]}"
        )

    # Collect all '[' positions, try each from last to first
    bracket_positions = [i for i, ch in enumerate(stripped) if ch == "["]
    for pos in reversed(bracket_positions):
        try:
            result = json.loads(stripped[pos : end + 1])
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            continue

    raise TriageClientError(
        f"Failed to parse JSON array from script output.\n"
        f"Raw output: {raw[:500]}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def fetch_triage_items(
    column: str = "Triage", board: str = ""
) -> list[TriageItem]:
    """Run ``Get-TriageItems.ps1`` and return parsed :class:`TriageItem` objects.

    Parameters
    ----------
    column:
        The board column to query (passed as ``-BoardColumn`` to the script).
    board:
        Board URL (e.g., 'https://dev.azure.com/.../t/TeamName/...') or a
        legacy board key. URLs are parsed to extract the team name passed as
        ``-Team`` to the script; plain keys are passed as ``-Board``.

    Raises
    ------
    TriageClientError
        If the script is missing, PowerShell is not found, or the output
        cannot be parsed.
    """
    script_path = _resolve_script_path()
    ps_path = _find_powershell()

    cmd = [
        ps_path,
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(script_path),
        "-BoardColumn", column,
    ]

    # Detect whether board is a URL or a legacy key
    team_name = _extract_team_from_url(board) if board.startswith("http") else None
    if team_name:
        cmd.extend(["-Team", team_name])
    else:
        cmd.extend(["-Board", board])
    log.info("Running triage script: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if stderr:
        log.debug("Triage script stderr:\n%s", stderr)

    if proc.returncode != 0:
        raise TriageClientError(
            f"Triage script exited with code {proc.returncode}.\n"
            f"stderr: {stderr[:1000]}"
        )

    if not stdout:
        log.warning("Triage script produced no stdout output")
        return []

    raw_items = _extract_json_array(stdout)
    items = [TriageItem.from_json(d) for d in raw_items]
    log.info("Parsed %d triage items from script output", len(items))
    return items
