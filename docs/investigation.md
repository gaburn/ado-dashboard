# Investigation Launcher Adapter

ADO Dashboard supports a pluggable **investigation backend** for AI-enriched triage and item investigation sessions.

---

## Default: NoOpLauncher

Out of the box, ADO Dashboard ships with `NoOpLauncher` as the active launcher.  It is fully functional but does not open any external process:

- **`build_item_investigation_prompt`** / **`build_board_investigation_prompt`** — return generic markdown prompts suitable for pasting into any AI assistant.
- **`launch`** — immediately returns `(False, "No investigation backend configured")`.
- **`discover_models`** / **`discover_agents`** — return `[]` (Settings screen shows a "No backend configured" placeholder).

AI enrichment on the Triage tab is skipped gracefully when launch fails.

---

## Configuring a Custom Launcher

Implement the `InvestigationLauncher` Protocol from `ado_dashboard.investigation`:

```python
from ado_dashboard.investigation import InvestigationLauncher, set_launcher

class MyLauncher:
    """Custom investigation backend."""

    def build_item_investigation_prompt(
        self,
        item_id: int,
        title: str,
        board_url: str,
        category: str,
        priority: int,
    ) -> str:
        return f"Investigate work item #{item_id}: {title}\n\nCategory: {category}, Priority: {priority}"

    def build_board_investigation_prompt(self, board_url: str, board_display_name: str) -> str:
        return f"Review triage board: {board_display_name}\nURL: {board_url}"

    def launch(
        self,
        prompt: str,
        title: str,
        *,
        cwd: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> tuple[bool, str]:
        # Open your AI backend here (subprocess, API call, etc.)
        # Return (True, "") on success or (False, error_message) on failure.
        return True, ""

    def discover_models(self) -> list[tuple[str, str]]:
        # Return [(display_name, value), ...] for the Settings screen dropdown.
        return [("GPT-4o", "gpt-4o"), ("GPT-4o mini", "gpt-4o-mini")]

    def discover_agents(self) -> list[tuple[str, str]]:
        return []


# Register your launcher at app startup (e.g., in your app's __init__ or main):
set_launcher(MyLauncher())
```

Call `set_launcher()` once before the Textual app runs — for example in a `pyproject.toml` entry-point wrapper or a custom `__main__.py` that imports ado-dashboard as a library.

---

## Protocol Reference

```python
class InvestigationLauncher(Protocol):
    def build_item_investigation_prompt(
        self, item_id: int, title: str, board_url: str, category: str, priority: int
    ) -> str: ...

    def build_board_investigation_prompt(
        self, board_url: str, board_display_name: str
    ) -> str: ...

    def launch(
        self,
        prompt: str,
        title: str,
        *,
        cwd: str | None = None,
        model: str | None = None,
        agent: str | None = None,
    ) -> tuple[bool, str]: ...

    def discover_models(self) -> list[tuple[str, str]]: ...
    def discover_agents(self) -> list[tuple[str, str]]: ...
```

All methods are required.  `launch` must return `(True, "")` on success or `(False, reason)` on failure.

---

## Registry API

```python
from ado_dashboard.investigation import get_launcher, set_launcher

# Read the active launcher:
launcher = get_launcher()

# Replace it:
set_launcher(MyLauncher())
```

`get_launcher()` always returns a valid launcher (defaults to `NoOpLauncher()` on first call).
