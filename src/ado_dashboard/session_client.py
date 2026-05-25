"""Async client that scans local Copilot session-state directories."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from wip_dashboard import config
from wip_dashboard.models import CopilotSession

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def fetch_sessions() -> list[CopilotSession]:
    """Scan ``COPILOT_SESSION_DIR`` for session subdirectories.

    Returns a list of :class:`CopilotSession` sorted with active sessions
    first, then by ``updated_at`` descending.  Never raises — logs warnings
    and returns an empty list on any systemic error.
    """
    session_dir = Path(config.COPILOT_SESSION_DIR).expanduser()
    if not session_dir.is_dir():
        log.warning("Copilot session dir not found: %s", session_dir)
        return []

    active_pids = await _get_active_session_pids()
    log.debug("Active session PIDs: %s", active_pids)

    try:
        entries: list[Path] = await asyncio.to_thread(
            lambda: [p for p in session_dir.iterdir() if p.is_dir()]
        )
    except OSError as exc:
        log.warning("Failed to list session dir %s: %s", session_dir, exc)
        return []

    max_age_secs = config.SESSION_MAX_AGE_DAYS * 86_400
    now_ts = datetime.now(tz=UTC).timestamp()

    sessions: list[CopilotSession] = []
    for entry in entries:
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        if (now_ts - mtime) > max_age_secs:
            continue

        session = await asyncio.to_thread(_parse_session, entry, active_pids)
        if session is not None:
            sessions.append(session)

    # Active first, then most-recently-updated first within each group.
    sessions.sort(key=lambda s: (not s.is_active, -s.updated_at.timestamp()))

    log.info(
        "Found %d Copilot sessions (%d active)",
        len(sessions),
        sum(1 for s in sessions if s.is_active),
    )
    return sessions


_MAX_TITLE_LEN = 80


def resume_session(session: CopilotSession) -> tuple[bool, str]:
    """Open a Copilot session in a new Windows Terminal tab (fire-and-forget).

    Returns ``(True, msg)`` on success, ``(False, msg)`` on failure.
    """
    wt_path = shutil.which("wt")
    if wt_path is None:
        return False, "Windows Terminal (wt.exe) not found"

    title = session.summary or session.id[:8]
    if len(title) > _MAX_TITLE_LEN:
        title = title[: _MAX_TITLE_LEN - 1] + "…"

    cmd: list[str] = [wt_path, "new-tab", "--title", title]

    if session.cwd:
        cmd.extend(["-d", session.cwd])

    cmd.extend(["--", "agency", "copilot", "--resume", session.id])

    try:
        subprocess.Popen(cmd)  # noqa: S603 — fire-and-forget
    except OSError as exc:
        log.error("Failed to launch Windows Terminal: %s", exc)
        return False, f"Failed to launch Windows Terminal: {exc}"

    log.info("Resumed session %s in new terminal tab", session.id[:8])
    return True, "Resumed session in new terminal tab"


def launch_investigation(
    prompt: str,
    title: str = "Triage Investigation",
    cwd: str | None = None,
    model: str = "",
    agent: str = "",
) -> tuple[bool, str]:
    """Launch a new investigation session via the configured launcher.

    Delegates to :func:`wip_dashboard.investigation.get_launcher` so the
    backend can be swapped without touching call sites.  See
    ``docs/investigation.md`` for how to configure a launcher.

    Returns ``(True, msg)`` on success, ``(False, msg)`` on failure.
    """
    from wip_dashboard.investigation import get_launcher
    return get_launcher().launch(prompt, title=title, cwd=cwd, model=model, agent=agent)


# ---------------------------------------------------------------------------
# Active-process detection
# ---------------------------------------------------------------------------
async def _get_active_session_pids() -> dict[str, int]:
    """Return ``{session_uuid: shell_pid}`` for running Copilot processes.

    Finds each ``copilot.exe --resume <uuid>`` process, then walks up the
    parent chain to locate the nearest ``pwsh`` / ``powershell`` / ``cmd``
    ancestor.  The *shell* PID is stored so that the window-focus feature
    can walk from the shell up to ``WindowsTerminal``.

    Falls back to the copilot PID itself when no shell ancestor is found.

    Returns an empty dict if PowerShell is unavailable or the query fails.
    """
    ps = shutil.which("pwsh") or shutil.which("powershell")
    if ps is None:
        log.warning("PowerShell not found on PATH; cannot detect active sessions")
        return {}

    cmd = [
        ps,
        "-NoProfile",
        "-Command",
        """
        # Bulk-fetch ALL processes in a single CIM call (avoids N+1 queries)
        $allProcs = Get-CimInstance Win32_Process -Property ProcessId, ParentProcessId, Name, CommandLine
        $procMap = @{}
        foreach ($p in $allProcs) { $procMap[[uint32]$p.ProcessId] = $p }

        $shells = @('pwsh', 'powershell', 'cmd')
        $results = @()

        foreach ($p in $allProcs) {
            if ($p.Name -ne 'copilot.exe') { continue }
            if (-not $p.CommandLine) { continue }
            if ($p.CommandLine -notmatch '--resume\\s+([0-9a-fA-F-]{36})') { continue }

            $uuid = $Matches[1]
            $shellPid = [int]$p.ProcessId  # fallback to copilot PID

            $current = $p.ParentProcessId
            for ($i = 0; $i -lt 10; $i++) {
                if (-not $current -or $current -eq 0) { break }
                $parent = $procMap[[uint32]$current]
                if (-not $parent) { break }
                $pName = $parent.Name -replace '\\.exe$', ''
                if ($pName -in $shells) {
                    $shellPid = [int]$current
                    break
                }
                $current = $parent.ParentProcessId
            }

            $results += @{ Id = $shellPid; Uuid = $uuid }
        }

        $results | ConvertTo-Json
        """,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        log.debug("Active sessions raw output: %r", stdout[:500])
    except OSError as exc:
        log.warning("Failed to run PowerShell for active sessions: %s", exc)
        return {}

    if not stdout:
        return {}

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        log.warning("Failed to parse PowerShell JSON output for active sessions")
        return {}

    # Single-process result is a dict rather than a list.
    if isinstance(data, dict):
        data = [data]

    result: dict[str, int] = {}
    for item in data:
        pid = item.get("Id")
        uuid = item.get("Uuid") or ""
        if pid and uuid:
            result[uuid] = int(pid)

    log.debug("Parsed active PIDs: %s", result)
    return result


# ---------------------------------------------------------------------------
# Session-directory parsing
# ---------------------------------------------------------------------------
def _parse_session(
    session_dir: Path,
    active_pids: dict[str, int],
) -> CopilotSession | None:
    """Parse a single session directory into a :class:`CopilotSession`.

    Returns ``None`` when the directory is missing critical files or is
    malformed (a warning is logged).
    """
    workspace_file = session_dir / "workspace.yaml"
    events_file = session_dir / "events.jsonl"

    # --- workspace.yaml (simple key: value, no YAML dependency) -------------
    if not workspace_file.exists():
        log.debug("Skipping session %s: no workspace.yaml", session_dir.name)
        return None

    try:
        yaml_text = workspace_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("Failed to read %s: %s", workspace_file, exc)
        return None

    fields = _parse_simple_yaml(yaml_text)

    session_id = fields.get("id", session_dir.name)
    summary = fields.get("summary", "")
    cwd = fields.get("cwd", "")
    git_root = fields.get("git_root", "")
    branch = fields.get("branch", "")
    created_at = _parse_yaml_datetime(fields.get("created_at", ""))
    updated_at = _parse_yaml_datetime(fields.get("updated_at", ""))

    # --- events.jsonl -------------------------------------------------------
    event_count = 0
    intent = ""
    copilot_version = ""

    if events_file.exists():
        try:
            event_count, intent, copilot_version = _parse_events(events_file)
        except OSError as exc:
            log.warning("Failed to read %s: %s", events_file, exc)

    is_active = session_id in active_pids
    pid = active_pids.get(session_id)

    return CopilotSession(
        id=session_id,
        summary=summary,
        cwd=cwd,
        git_root=git_root,
        branch=branch,
        created_at=created_at,
        updated_at=updated_at,
        is_active=is_active,
        pid=pid,
        intent=intent,
        event_count=event_count,
        copilot_version=copilot_version,
    )


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def _parse_simple_yaml(text: str) -> dict[str, str]:
    """Parse a flat YAML file into a dict via simple string splitting.

    Only handles top-level ``key: value`` pairs.  Ignores nested structures,
    comments, list items, and multi-line values.
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        colon_idx = stripped.find(":")
        if colon_idx == -1:
            continue
        key = stripped[:colon_idx].strip()
        value = stripped[colon_idx + 1 :].strip()
        # Strip surrounding quotes if present.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def _parse_yaml_datetime(raw: str) -> datetime:
    """Best-effort parse of an ISO-8601 datetime string from YAML.

    Falls back to *now (UTC)* when the string is empty or unparseable.
    """
    if not raw:
        return datetime.now(tz=UTC)
    try:
        cleaned = raw.rstrip("Z")
        # Truncate fractional seconds to 6 digits (Python max).
        if "." in cleaned:
            base, frac = cleaned.split(".", 1)
            cleaned = f"{base}.{frac[:6]}"
        # Append UTC offset when none is present.
        has_offset = "+" in cleaned or "-" in cleaned[10:]
        if not has_offset:
            cleaned = f"{cleaned}+00:00"
        return datetime.fromisoformat(cleaned)
    except (ValueError, IndexError):
        return datetime.now(tz=UTC)


def _parse_events(events_file: Path) -> tuple[int, str, str]:
    """Extract ``(event_count, intent, copilot_version)`` from *events.jsonl*.

    * ``event_count`` — total number of non-blank lines.
    * ``intent`` — ``intent`` field from the most recent ``report_intent`` event
      found in the last ~50 lines.
    * ``copilot_version`` — version string from the first ``session.start`` event.
    """
    text = events_file.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    event_count = len(lines)

    copilot_version = ""
    intent = ""

    # First line → session.start / copilot version.
    if lines:
        try:
            first = json.loads(lines[0])
            if first.get("type") == "session.start":
                copilot_version = (
                    first.get("copilot_version", "")
                    or first.get("version", "")
                )
        except (json.JSONDecodeError, AttributeError):
            pass

    # Last ~50 lines, scan backwards for the most recent report_intent.
    tail = lines[-50:] if len(lines) > 50 else lines
    for line in reversed(tail):
        try:
            event = json.loads(line)
            if event.get("type") == "report_intent":
                intent = event.get("intent", "") or event.get("message", "")
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    return event_count, intent, copilot_version
