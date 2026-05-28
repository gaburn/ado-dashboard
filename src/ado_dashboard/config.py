"""Configuration constants with environment-variable, config-file, and CLI-arg overrides.

Resolution order (highest priority first):
    1. CLI args          — ``apply_overrides()``
    2. Environment vars  — ``os.environ``
    3. Config file       — ``load_from_file()``
    4. Built-in defaults — the ``_DEFAULT_*`` constants below

All triage board options are user-configured (no built-in defaults).  Add them
via the in-app Settings screen (``s``) or by editing ``triage_board_options``
in the config file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Demo mode — set by --demo CLI flag or ADO_DASHBOARD_DEMO=1 env var.
# When True, all data is served from fictional fixture data (no ADO calls).
# ---------------------------------------------------------------------------
DEMO_MODE: bool = os.environ.get("ADO_DASHBOARD_DEMO", "").strip() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Defaults  (intentionally empty/generic — the setup wizard fills these in)
# ---------------------------------------------------------------------------
_DEFAULT_ORG_URL = ""
_DEFAULT_PROJECT = ""
_DEFAULT_USER_EMAIL = ""


# ---------------------------------------------------------------------------
# Repository root (for launching investigation sessions with skill access)
# ---------------------------------------------------------------------------
def _find_repo_root() -> str:
    """Walk up from this file to find the git root."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".git").is_dir():
            return str(parent)
    return ""


# ADO_DASHBOARD_REPO_ROOT overrides automatic git-root detection.
# WIP_DASHBOARD_REPO_ROOT is the deprecated predecessor — checked as fallback.
def _resolve_repo_root() -> str:
    import warnings  # stdlib — safe to import lazily here
    val = os.environ.get("ADO_DASHBOARD_REPO_ROOT")
    if val:
        return val
    val = os.environ.get("WIP_DASHBOARD_REPO_ROOT")
    if val:
        warnings.warn(
            "WIP_DASHBOARD_REPO_ROOT is deprecated; rename to ADO_DASHBOARD_REPO_ROOT."
            " This fallback will be removed in v0.4.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return val
    return _find_repo_root()


REPO_ROOT: str = _resolve_repo_root()

# ---------------------------------------------------------------------------
# Resolved values — env vars win, then defaults.
# ---------------------------------------------------------------------------
ORG_URL: str = os.environ.get("ADO_ORG_URL", _DEFAULT_ORG_URL)
PROJECT: str = os.environ.get("ADO_PROJECT", _DEFAULT_PROJECT)
USER_EMAIL: str = os.environ.get("ADO_USER_EMAIL", _DEFAULT_USER_EMAIL)

# Projects to query for pull requests (az repos pr list requires --project).
PROJECTS: list[str] = []

# Triage script — optional override; see Get-TriageItems.ps1.example for the contract.
# ---------------------------------------------------------------------------
TRIAGE_SCRIPT_PATH: str = os.environ.get("TRIAGE_SCRIPT_PATH", "")

# ---------------------------------------------------------------------------
# Triage board selection
# Boards are user-configured — no built-in defaults.
# Add them via Settings (s) or the triage_board_options key in config.json.
# ---------------------------------------------------------------------------
TRIAGE_BOARD_OPTIONS: list[tuple[str, str]] = []
TRIAGE_BOARD: str = os.environ.get("TRIAGE_BOARD", "")

# Optional: repo name used to linkify PR references in triage descriptions.
# Leave empty to display PR references as plain text (safe default).
# Example: "MyRepo" → links to {ORG_URL}/{PROJECT}/_git/MyRepo/pullrequest/{id}
TRIAGE_PR_REPO: str = os.environ.get("TRIAGE_PR_REPO", "")

# ---------------------------------------------------------------------------
# Investigation sessions
# ---------------------------------------------------------------------------
INVESTIGATIONS_DIR: str = os.environ.get(
    "INVESTIGATIONS_DIR",
    os.path.expanduser("~/.ado-dashboard/investigations"),
)
INVESTIGATION_MODEL: str = os.environ.get("INVESTIGATION_MODEL", "")
INVESTIGATION_AGENT: str = os.environ.get("INVESTIGATION_AGENT", "")

# ---------------------------------------------------------------------------
# AI triage mode and cache
# ---------------------------------------------------------------------------
AI_TRIAGE_MODE: str = os.environ.get("AI_TRIAGE_MODE", "copilot")  # "copilot" or "off"
TRIAGE_CACHE_DIR: str = os.environ.get(
    "TRIAGE_CACHE_DIR",
    os.path.expanduser("~/.ado-dashboard/triage"),
)
TRIAGE_CACHE_MAX_AGE_SECONDS: int = int(os.environ.get("TRIAGE_CACHE_MAX_AGE", "1800"))

# ---------------------------------------------------------------------------
# Copilot session tracking
# ---------------------------------------------------------------------------
COPILOT_SESSION_DIR: str = os.environ.get(
    "COPILOT_SESSION_DIR",
    os.path.expanduser("~/.copilot/session-state"),
)
SESSION_MAX_AGE_DAYS: int = int(os.environ.get("SESSION_MAX_AGE_DAYS", "7"))


# ---------------------------------------------------------------------------
# URL helpers (internal)
# ---------------------------------------------------------------------------

def _normalize_org_url(raw: str) -> str:
    """Ensure the org URL is a full HTTPS URI.

    Accepts:
      - Full URL:  ``https://dev.azure.com/myorg``  → unchanged
      - Bare name: ``myorg``                         → ``https://dev.azure.com/myorg``

    Trailing slashes are stripped in all cases.
    """
    raw = raw.strip().rstrip("/")
    if raw and not raw.startswith(("http://", "https://")):
        raw = f"https://dev.azure.com/{raw}"
    return raw


# ---------------------------------------------------------------------------
# Config-file loading (layer between env vars and built-in defaults)
# ---------------------------------------------------------------------------

def load_from_file(file_data: dict) -> None:
    """Apply values from the config-file dict, but only when the
    corresponding environment variable is **not** already set.

    Call this *before* :func:`apply_overrides` so CLI args still win.
    """
    global ORG_URL, PROJECT, USER_EMAIL, PROJECTS  # noqa: PLW0603
    global INVESTIGATIONS_DIR, INVESTIGATION_MODEL, INVESTIGATION_AGENT  # noqa: PLW0603
    global AI_TRIAGE_MODE, TRIAGE_CACHE_DIR, TRIAGE_CACHE_MAX_AGE_SECONDS  # noqa: PLW0603
    global COPILOT_SESSION_DIR, SESSION_MAX_AGE_DAYS  # noqa: PLW0603
    global TRIAGE_SCRIPT_PATH, TRIAGE_BOARD, TRIAGE_BOARD_OPTIONS, TRIAGE_PR_REPO  # noqa: PLW0603

    if "ADO_ORG_URL" not in os.environ and "ado_org_url" in file_data:
        ORG_URL = _normalize_org_url(file_data["ado_org_url"])

    if "ADO_PROJECT" not in os.environ and "ado_project" in file_data:
        PROJECT = file_data["ado_project"]

    if "ADO_USER_EMAIL" not in os.environ and "user_email" in file_data:
        USER_EMAIL = file_data["user_email"]

    # PROJECTS has no dedicated env var — always take from file.
    if "ado_projects" in file_data:
        PROJECTS = file_data["ado_projects"]

    if "TRIAGE_SCRIPT_PATH" not in os.environ and "triage_script_path" in file_data:
        TRIAGE_SCRIPT_PATH = file_data["triage_script_path"]

    if "TRIAGE_BOARD" not in os.environ and "triage_board" in file_data:
        TRIAGE_BOARD = file_data["triage_board"]

    if "triage_board_options" in file_data:
        raw = file_data["triage_board_options"]
        if isinstance(raw, list) and raw:
            TRIAGE_BOARD_OPTIONS = [(item[0], item[1]) for item in raw if len(item) >= 2]

    if "TRIAGE_PR_REPO" not in os.environ and "triage_pr_repo" in file_data:
        TRIAGE_PR_REPO = file_data["triage_pr_repo"]

    if "INVESTIGATIONS_DIR" not in os.environ and "investigations_dir" in file_data:
        INVESTIGATIONS_DIR = file_data["investigations_dir"]

    if "INVESTIGATION_MODEL" not in os.environ and "investigation_model" in file_data:
        INVESTIGATION_MODEL = file_data["investigation_model"]

    if "INVESTIGATION_AGENT" not in os.environ and "investigation_agent" in file_data:
        INVESTIGATION_AGENT = file_data["investigation_agent"]

    if "AI_TRIAGE_MODE" not in os.environ and "ai_triage_mode" in file_data:
        AI_TRIAGE_MODE = file_data["ai_triage_mode"]

    if "TRIAGE_CACHE_DIR" not in os.environ and "triage_cache_dir" in file_data:
        TRIAGE_CACHE_DIR = file_data["triage_cache_dir"]

    if "TRIAGE_CACHE_MAX_AGE" not in os.environ and "triage_cache_max_age_seconds" in file_data:
        TRIAGE_CACHE_MAX_AGE_SECONDS = int(file_data["triage_cache_max_age_seconds"])

    if "COPILOT_SESSION_DIR" not in os.environ and "copilot_session_dir" in file_data:
        COPILOT_SESSION_DIR = file_data["copilot_session_dir"]

    if "SESSION_MAX_AGE_DAYS" not in os.environ and "session_max_age_days" in file_data:
        SESSION_MAX_AGE_DAYS = int(file_data["session_max_age_days"])


# ---------------------------------------------------------------------------
# CLI-arg overrides (highest priority)
# ---------------------------------------------------------------------------

def apply_overrides(namespace: Any) -> None:
    """Apply CLI-arg overrides from an argparse-style namespace object.

    Only attributes that are present *and* not ``None`` will override the
    module-level values.  Call this once at startup, before any data fetching.
    """
    global ORG_URL, PROJECT, USER_EMAIL, PROJECTS  # noqa: PLW0603
    global TRIAGE_BOARD  # noqa: PLW0603

    if getattr(namespace, "org_url", None) is not None:
        ORG_URL = _normalize_org_url(namespace.org_url)
    if getattr(namespace, "project", None) is not None:
        PROJECT = namespace.project
    if getattr(namespace, "user_email", None) is not None:
        USER_EMAIL = namespace.user_email
    if getattr(namespace, "projects", None) is not None:
        value = namespace.projects
        if isinstance(value, str):
            PROJECTS = [p.strip() for p in value.split(",") if p.strip()]
        elif isinstance(value, list):
            PROJECTS = value
    if getattr(namespace, "triage_board", None) is not None:
        TRIAGE_BOARD = namespace.triage_board


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def pr_url(repo_name: str, pr_id: int) -> str:
    """Return the browser URL for a pull request."""
    return f"{ORG_URL}/{PROJECT}/_git/{repo_name}/pullrequest/{pr_id}"


def work_item_url(wi_id: int) -> str:
    """Return the browser URL for a work item."""
    return f"{ORG_URL}/{PROJECT}/_workitems/edit/{wi_id}"
