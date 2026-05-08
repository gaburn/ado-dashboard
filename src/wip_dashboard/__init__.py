"""WIP Dashboard — interactive terminal dashboard for Azure DevOps PRs and work items."""

import subprocess
from pathlib import Path

__version__ = "0.2.0"

_PACKAGE_DIR = str(Path(__file__).resolve().parent)


def _get_git_build_hash() -> str:
    """Return the short git commit hash (with +dirty suffix if uncommitted changes exist).

    Falls back to ``"dev"`` when git is unavailable or the working directory
    is not inside a repository.  The result is computed once at import time.
    """
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            cwd=_PACKAGE_DIR,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return "dev"


__build__ = _get_git_build_hash()
