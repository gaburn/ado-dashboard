"""Investigation adapter interface and built-in implementations.

The ``InvestigationLauncher`` Protocol defines how wip-dashboard launches
investigation sessions, builds prompts, and discovers available models and
agents.  Swap in your own implementation to integrate with any AI assistant.

Built-in adapters
-----------------
``NoOpLauncher``  (default)
    Returns generic prompts and reports "no backend configured" when asked to
    launch.  Safe default for OSS installs — see ``docs/investigation.md`` for
    how to configure a real backend.

``AgencyLauncher``  (Microsoft-internal example)
    Uses the ``agency copilot`` CLI to launch investigation sessions in a new
    Windows Terminal tab.  Requires ``wt.exe``, ``pwsh``/``powershell``, and
    ``agency`` on PATH.  See ``docs/investigation.md`` for details.

Usage
-----
    # In app startup — pick a launcher (defaults to NoOpLauncher):
    from wip_dashboard import investigation
    investigation.set_launcher(investigation.AgencyLauncher())

    # Anywhere else:
    launcher = investigation.get_launcher()
    ok, msg = launcher.launch(prompt, title="...", cwd=None, model="", agent="")
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)


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
# AgencyLauncher — Microsoft-internal example adapter
#
# Uses the `agency copilot` CLI (https://aka.ms/agency-cli) to launch
# investigation sessions in a new Windows Terminal tab.  Requires:
#   - Windows Terminal  (wt.exe)
#   - PowerShell 7+     (pwsh or powershell)
#   - agency CLI        (agency)
#
# External users can use this as a template for their own launcher.
# See docs/investigation.md for the adapter contract.
# ---------------------------------------------------------------------------

class AgencyLauncher:
    """Concrete launcher that uses the ``agency copilot`` CLI.

    This is a Microsoft-internal example adapter.  The ``agency`` CLI is not
    publicly distributed.  External users should implement their own
    ``InvestigationLauncher`` (e.g. wrapping ``gh copilot`` or ``aider``).
    """

    _MAX_TITLE_LEN = 80

    def build_board_prompt(self, board_url: str, board_display_name: str) -> str:
        return (
            f"Triage the '{board_display_name}' board at {board_url}, "
            "then investigate all P1 and P2 items.  "
            "For P3 items, only investigate blocking issues and bugs."
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
            f"Triage the board at {board_url}.  After completing the triage, "
            f"write the results as a JSON file to: {output_path}\n\n"
            f"{_AI_TRIAGE_JSON_SCHEMA}"
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
        """Open a new Windows Terminal tab running ``agency copilot --yolo``."""
        wt_path = shutil.which("wt")
        if wt_path is None:
            return False, "Windows Terminal (wt.exe) not found"

        agency_path = shutil.which("agency")
        if agency_path is None:
            return False, "agency CLI not found on PATH"

        if len(title) > self._MAX_TITLE_LEN:
            title = title[: self._MAX_TITLE_LEN - 1] + "…"

        tmp_dir = Path(tempfile.gettempdir()) / "wip-dashboard"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = tmp_dir / "prompt.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        agency_args = [f'& "{agency_path}" copilot --yolo']
        if agent:
            agency_args.append(f"--agent {agent}")
        if model:
            agency_args.append(f"--model {model}")
        agency_args.append(f'-i (Get-Content -Raw "{prompt_file}")')

        launcher_file = tmp_dir / "launch-triage.ps1"
        launcher_file.write_text(" ".join(agency_args) + "\n", encoding="utf-8")

        cmd: list[str] = [wt_path, "new-tab", "--title", title]
        if cwd:
            cmd.extend(["-d", cwd])
        cmd.extend([
            "--", "pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(launcher_file),
        ])

        try:
            import subprocess as _sp
            _sp.Popen(cmd)  # noqa: S603 — fire-and-forget
        except OSError as exc:
            log.error("Failed to launch investigation: %s", exc)
            return False, f"Failed to launch investigation: {exc}"

        log.info("Launched investigation in new terminal tab: %s", title)
        return True, "Investigation launched in new terminal tab"

    def discover_models(self) -> list[tuple[str, str]]:
        """Parse available models from ``agency copilot --help``."""
        import re as _re

        agency = shutil.which("agency")
        if not agency:
            return []

        try:
            result = subprocess.run(
                [agency, "copilot", "--help"],
                capture_output=True, text=True, timeout=15,
            )
            help_text = result.stdout + result.stderr
        except (OSError, subprocess.TimeoutExpired):
            return []

        model_ids: list[str] = []
        in_model = False
        for line in help_text.split("\n"):
            if "--model" in line and "<" in line:
                in_model = True
                model_ids.extend(
                    _re.findall(r"\b(claude-[\w.-]+|gpt-[\w.-]+|gemini-[\w.-]+)\b", line)
                )
            elif in_model:
                if line.strip().startswith("--") or not line.strip():
                    break
                model_ids.extend(
                    _re.findall(r"\b(claude-[\w.-]+|gpt-[\w.-]+|gemini-[\w.-]+)\b", line)
                )

        if not model_ids:
            return []

        seen: set[str] = set()
        unique: list[str] = []
        for m in model_ids:
            if m not in seen:
                seen.add(m)
                unique.append(m)

        def _humanize(model_id: str) -> str:
            return " ".join(p.capitalize() for p in model_id.split("-"))

        return [("Default", "")] + [(_humanize(m), m) for m in unique]

    def discover_agents(self) -> list[tuple[str, str]]:
        """Discover available agents from personal and repo agent directories."""
        from wip_dashboard import config as _config

        agents: list[tuple[str, str]] = [
            ("Orchestrator", "orchestrator"),
            ("Planner", "planner"),
            ("Coder", "coder"),
            ("Designer", "designer"),
            ("Explorer", "explore"),
            ("Task Runner", "task"),
            ("General Purpose", "general-purpose"),
            ("Code Review", "code-review"),
        ]
        seen = {a[1] for a in agents}

        for agent_dir in [
            Path.home() / ".copilot" / "agents",
            Path.home() / ".claude" / "agents",
        ]:
            if agent_dir.is_dir():
                for child in sorted(agent_dir.iterdir()):
                    if child.is_dir() and child.name not in seen:
                        display = child.name.replace("-", " ").replace("_", " ").title()
                        agents.append((display, child.name))
                        seen.add(child.name)

        repo_root = _config.REPO_ROOT
        if repo_root:
            for rel in [".github/agents", ".claude/agents"]:
                agent_dir = Path(repo_root) / rel
                if agent_dir.is_dir():
                    for child in sorted(agent_dir.iterdir()):
                        if child.is_dir() and child.name not in seen:
                            display = child.name.replace("-", " ").replace("_", " ").title()
                            agents.append((f"{display} (repo)", child.name))
                            seen.add(child.name)

        return agents


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
