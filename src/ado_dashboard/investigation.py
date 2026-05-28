"""Investigation adapter interface and built-in implementations.

The ``InvestigationLauncher`` Protocol defines how ado-dashboard launches
investigation sessions, builds prompts, and discovers available models and
agents.  Swap in your own implementation to integrate with any AI assistant.

Built-in adapters
-----------------
``NoOpLauncher``  (default)
    Returns generic prompts and reports "no backend configured" when asked to
    launch.  Safe default for OSS installs — see ``docs/investigation.md`` for
    how to write a custom launcher (e.g. wrapping ``gh copilot``, ``aider``,
    or any other AI CLI).

Usage
-----
    # In app startup — pick a launcher (defaults to NoOpLauncher):
    from ado_dashboard import investigation
    investigation.set_launcher(MyLauncher())

    # Anywhere else:
    launcher = investigation.get_launcher()
    ok, msg = launcher.launch(prompt, title="...", cwd=None, model="", agent="")
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class InvestigationLauncher(Protocol):
    """Adapter interface for investigation-session backends."""

    def build_board_prompt(self, board_url: str, board_display_name: str) -> str:
        """Return a prompt to investigate an entire triage board."""
        ...

    def build_item_prompt(
        self,
        item_id: int,
        title: str,
        board_url: str,
        category: str = "",
        priority_label: str = "",
    ) -> str:
        """Return a prompt to investigate a single triage item."""
        ...

    def build_ai_triage_prompt(self, board_url: str, output_path: str) -> str:
        """Return a prompt that instructs the AI to write triage JSON to output_path."""
        ...

    def launch(
        self,
        prompt: str,
        *,
        title: str = "Investigation",
        cwd: str | None = None,
        model: str = "",
        agent: str = "",
    ) -> tuple[bool, str]:
        """Launch an investigation session. Returns (success, message)."""
        ...

    def discover_models(self) -> list[tuple[str, str]]:
        """Return ``[(display_name, model_id), ...]`` available to this launcher."""
        ...

    def discover_agents(self) -> list[tuple[str, str]]:
        """Return ``[(display_name, agent_id), ...]`` available to this launcher."""
        ...


# ---------------------------------------------------------------------------
# Built-in JSON output schema (shared by all launchers)
# ---------------------------------------------------------------------------

_AI_TRIAGE_JSON_SCHEMA = (
    "The JSON file MUST have this exact structure:\n"
    "{\n"
    '  "board": "<board identifier>",\n'
    '  "timestamp": "<ISO 8601 UTC timestamp>",\n'
    '  "items": [\n'
    "    {\n"
    '      "id": <work_item_id>,\n'
    '      "category": "<one of: Blocking Issue, Bug / Behavior, PR Review, Feature Request, Support Question>",\n'
    '      "priority": <1-4>,\n'
    '      "why": "<concise explanation, max 55 chars>"\n'
    "    }\n"
    "  ],\n"
    '  "action_plan": "<2-3 sentence recommended action plan>"\n'
    "}\n\n"
    "Write the file atomically: write to a .tmp file first, then rename to "
    "the final path.  The file must contain ONLY valid JSON — no markdown, "
    "code fences, or extra text."
)


# ---------------------------------------------------------------------------
# NoOpLauncher — safe default for OSS installs
# ---------------------------------------------------------------------------

class NoOpLauncher:
    """Stub launcher used when no investigation backend is configured.

    Investigation prompts are still built generically, but ``launch`` always
    returns failure with a message directing the user to the docs.
    """

    def build_board_prompt(self, board_url: str, board_display_name: str) -> str:
        return (
            f"Investigate the '{board_display_name}' triage board at {board_url}. "
            "Prioritize P1 and P2 items.  For P3 items, focus on blocking issues and bugs."
        )

    def build_item_prompt(
        self,
        item_id: int,
        title: str,
        board_url: str,
        category: str = "",
        priority_label: str = "",
    ) -> str:
        parts = [f"Investigate work item #{item_id}: '{title}'."]
        if category:
            parts.append(f"Category: {category}.")
        if priority_label:
            parts.append(f"Priority: {priority_label}.")
        return " ".join(parts)

    def build_ai_triage_prompt(self, board_url: str, output_path: str) -> str:
        return (
            f"Triage the board at {board_url} and write the results as a JSON "
            f"file to: {output_path}\n\n{_AI_TRIAGE_JSON_SCHEMA}"
        )

    def launch(
        self,
        prompt: str,
        *,
        title: str = "Investigation",
        cwd: str | None = None,
        model: str = "",
        agent: str = "",
    ) -> tuple[bool, str]:
        return False, (
            "No investigation backend is configured — "
            "see docs/investigation.md to set up a launcher."
        )

    def discover_models(self) -> list[tuple[str, str]]:
        return []

    def discover_agents(self) -> list[tuple[str, str]]:
        return []


# ---------------------------------------------------------------------------
# Global launcher registry
# ---------------------------------------------------------------------------

_launcher: InvestigationLauncher = NoOpLauncher()


def get_launcher() -> InvestigationLauncher:
    """Return the currently active investigation launcher."""
    return _launcher


def set_launcher(launcher: InvestigationLauncher) -> None:
    """Replace the active launcher (call once at app startup)."""
    global _launcher  # noqa: PLW0603
    _launcher = launcher
