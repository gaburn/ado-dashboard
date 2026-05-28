"""Prompt builders for launching investigation sessions.

All prompt building is delegated to the active ``InvestigationLauncher``
(see :mod:`wip_dashboard.investigation`).  These module-level functions are
thin wrappers kept for backward compatibility with existing call sites.

To customise prompts, configure a different launcher before the app starts::

    from wip_dashboard import investigation
    investigation.set_launcher(MyLauncher())
"""

from __future__ import annotations

from wip_dashboard.investigation import get_launcher


def board_key_from_url(url: str) -> str:
    """Extract a short board key from a board URL.

    The key is the URL-decoded team-name segment that follows
    ``/_boards/board/t/`` in ADO board URLs.  Falls back to ``"board"``
    when the URL doesn't match.

    This function is kept for backward compatibility.  Prompt builders no
    longer rely on internal board-key mappings.
    """
    from urllib.parse import unquote

    try:
        marker = "/_boards/board/t/"
        idx = url.index(marker)
        rest = url[idx + len(marker):]
        team = unquote(rest.split("/")[0])
        return team.lower().replace(" ", "-") if team else "board"
    except (ValueError, IndexError):
        return "board"


# Backward-compat alias
_board_key_from_url = board_key_from_url


def build_board_investigation_prompt(board_url: str, board_display_name: str) -> str:
    """Build a prompt to triage an entire board and investigate all items."""
    return get_launcher().build_board_prompt(board_url, board_display_name)


def build_item_investigation_prompt(
    item_id: int,
    title: str,
    board_url: str,
    category: str = "",
    priority_label: str = "",
) -> str:
    """Build a prompt to investigate a single triage item."""
    return get_launcher().build_item_prompt(
        item_id, title, board_url, category, priority_label
    )


def build_ai_triage_prompt(board_url: str, output_path: str) -> str:
    """Build a prompt to run AI triage and write structured JSON results."""
    return get_launcher().build_ai_triage_prompt(board_url, output_path)

