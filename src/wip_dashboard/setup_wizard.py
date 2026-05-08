"""First-run setup wizard — interactive prompts before the TUI launches.

Produces a JSON config file in the platform-specific user config directory
(via *platformdirs*).  The wizard is skipped automatically in non-interactive
environments (CI, piped stdin).
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from platformdirs import user_config_path

log = logging.getLogger(__name__)

_APP_NAME = "wip-dashboard"
_CONFIG_VERSION = 1


# ---------------------------------------------------------------------------
# Config file location
# ---------------------------------------------------------------------------

def config_file_path() -> Path:
    """Return the canonical path to the JSON config file.

    Creates the parent directory if it does not exist.
    """
    return user_config_path(_APP_NAME, ensure_exists=True) / "config.json"


def config_file_exists() -> bool:
    """Return *True* when the config file exists and contains valid JSON."""
    path = config_file_path()
    if not path.is_file():
        return False
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except (json.JSONDecodeError, OSError):
        return False


def load_config() -> dict:
    """Read and return the parsed config JSON.  Empty dict on any failure."""
    try:
        return json.loads(config_file_path().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return {}


def save_config(data: dict) -> Path:
    """Write *data* as JSON to the config file and return the path."""
    path = config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    log.info("Config saved to %s", path)
    return path


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _prompt(label: str, default: str = "") -> str:
    """Prompt the user for a single value with an optional default."""
    suffix = f" [{default}]" if default else ""
    raw = input(f"  {label}{suffix}: ").strip()
    return raw if raw else default


def _prompt_list(label: str, defaults: list[str] | None = None) -> list[str]:
    """Prompt for a comma-separated list with optional defaults."""
    default_str = ", ".join(defaults) if defaults else ""
    raw = _prompt(label, default_str)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

def _try_detect_email() -> str:
    """Attempt to auto-detect the user email via ``az account show``."""
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "user.name", "-o", "tsv"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        email = result.stdout.strip()
        if email:
            return email
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        log.debug("az account show failed: %s", exc)
    return ""


# ---------------------------------------------------------------------------
# Interactive wizard
# ---------------------------------------------------------------------------

def run_setup(existing_config: dict | None = None) -> dict:
    """Run the interactive first-run wizard and return the config dict.

    Parameters
    ----------
    existing_config:
        Previously saved config to use as defaults for each prompt.
        Pass ``None`` (or ``{}``) for a fresh setup.

    Returns
    -------
    dict
        The completed configuration ready to be passed to :func:`save_config`.
    """
    if not sys.stdin.isatty():
        log.warning("Non-interactive session detected — skipping setup wizard.")
        return existing_config or {}

    cfg = existing_config or {}

    print()
    print("=" * 60)
    print("  WIP Dashboard — First-Run Setup")
    print("=" * 60)
    print()

    # --- ADO org URL ---
    ado_org_url = _prompt(
        "ADO organization URL",
        cfg.get("ado_org_url", "https://dev.azure.com/<your-org>"),
    )
    # Treat the placeholder as empty — don't persist it literally.
    if ado_org_url == "https://dev.azure.com/<your-org>":
        ado_org_url = ""

    # --- Projects for PR queries ---
    ado_projects = _prompt_list(
        "Projects for PR queries (comma-separated)",
        cfg.get("ado_projects") or [],
    )

    # --- Project for work items ---
    default_project = cfg.get("ado_project") or (ado_projects[0] if ado_projects else "")
    ado_project = _prompt("Project for work items", default_project)

    # --- User email (auto-detect) ---
    detected_email = _try_detect_email()
    default_email = cfg.get("user_email") or detected_email
    if detected_email and detected_email != default_email:
        # Show auto-detected value when it differs from existing config.
        print(f"    (auto-detected: {detected_email})")
    user_email = _prompt("Email address", default_email)
    while not user_email:
        print("    Email is required.")
        user_email = _prompt("Email address", default_email)

    # --- Copilot session dir ---
    copilot_session_dir = _prompt(
        "Copilot session directory",
        cfg.get("copilot_session_dir", "~/.copilot/session-state"),
    )

    # --- Session max age ---
    default_max_age = str(cfg.get("session_max_age_days", 7))
    session_max_age_days = int(_prompt("Session max age (days)", default_max_age) or default_max_age)

    # --- Triage boards ---
    print()
    print("  Triage boards (optional — press Enter to skip, configure later in Settings)")
    existing_boards: list[list[str]] = cfg.get("triage_board_options", [])
    triage_board_options: list[list[str]] = []
    if existing_boards:
        print(f"    Existing boards: {', '.join(b[0] for b in existing_boards)}")
        keep = _prompt("Keep existing boards? (y/n)", "y").lower()
        if keep == "y":
            triage_board_options = list(existing_boards)

    while True:
        board_name = _prompt("  Board name (or Enter to finish)", "")
        if not board_name:
            break
        board_url = _prompt("  Board URL", "")
        if board_url:
            triage_board_options.append([board_name, board_url])
        else:
            print("    Skipped (no URL provided).")

    print()

    data: dict = {
        "_config_version": _CONFIG_VERSION,
        "ado_org_url": ado_org_url,
        "ado_projects": ado_projects,
        "ado_project": ado_project,
        "user_email": user_email,
        "copilot_session_dir": copilot_session_dir,
        "session_max_age_days": session_max_age_days,
    }
    if triage_board_options:
        data["triage_board_options"] = triage_board_options

    path = save_config(data)
    print(f"  Config saved to {path}")
    print()
    return data
