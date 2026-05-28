"""Settings screen — editable config fields with save/cancel."""

from __future__ import annotations

import logging
from functools import lru_cache

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Switch

from ado_dashboard import config
from ado_dashboard.investigation import get_launcher
from ado_dashboard.setup_wizard import save_config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config field definitions
# ---------------------------------------------------------------------------

# (config_key, label_text, is_switch)
_FIELDS: list[tuple[str, str, bool]] = [
    ("ado_org_url", "ADO Organization URL", False),
    ("ado_projects", "ADO Projects (comma-separated)", False),
    ("ado_project", "ADO Project (work items)", False),
    ("user_email", "User Email", False),
    ("copilot_session_dir", "Copilot Session Directory", False),
    ("session_max_age_days", "Session Max Age (days)", False),
]

# Map config keys to module-level attribute names in config module.
_CONFIG_ATTR_MAP: dict[str, str] = {
    "ado_org_url": "ORG_URL",
    "ado_projects": "PROJECTS",
    "ado_project": "PROJECT",
    "user_email": "USER_EMAIL",
    "copilot_session_dir": "COPILOT_SESSION_DIR",
    "session_max_age_days": "SESSION_MAX_AGE_DAYS",
}


def _humanize_model(model_id: str) -> str:
    """Convert a model ID like 'claude-sonnet-4.5' to 'Claude Sonnet 4.5'."""
    parts = model_id.split("-")
    result = []
    for part in parts:
        if part[0:1].isalpha():
            result.append(part.capitalize())
        else:
            result.append(part)
    return " ".join(result)


@lru_cache(maxsize=1)
def _discover_models() -> list[tuple[str, str]]:
    """Return model options from the active investigation launcher."""
    options = get_launcher().discover_models()
    # If the launcher returns nothing, surface a placeholder so the Select
    # widget has at least one item (Textual requires non-empty options).
    if not options:
        return [("No backend configured", "")]
    return options


@lru_cache(maxsize=1)
def _discover_agents() -> list[tuple[str, str]]:
    """Return agent options from the active investigation launcher."""
    options = get_launcher().discover_agents()
    if not options:
        return [("No backend configured", "")]
    return options


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


class SettingsScreen(Screen[bool]):
    """Editable settings form. Returns True on save, False on cancel."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._board_counter: int = 0

    # ---- compose ----------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="settings-form"):
            yield Static("⚙ Settings", classes="section-heading")
            for key, label_text, is_switch in _FIELDS:
                yield Label(label_text)
                if is_switch:
                    yield Switch(id=key)
                else:
                    yield Input(id=key, placeholder=label_text)
            yield Label("Triage Boards")
            yield Static(
                "See docs/triage-and-investigation.md for setup instructions.",
                classes="settings-hint",
            )
            yield Vertical(id="boards-list")
            yield Button("＋ Add Board", id="add-board", variant="default")
            yield Label("Investigation Model")
            yield Select(
                _discover_models(),
                value=config.INVESTIGATION_MODEL,
                allow_blank=False,
                id="investigation-model-select",
            )
            yield Label("Investigation Agent")
            yield Select(
                _discover_agents(),
                value=config.INVESTIGATION_AGENT,
                allow_blank=False,
                id="investigation-agent-select",
            )
            with Horizontal(classes="settings-buttons"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")
        yield Footer()

    def _make_board_row(self, name: str = "", url: str = "") -> Horizontal:
        """Create a single board row with Name input, URL input, and remove button."""
        self._board_counter += 1
        idx = self._board_counter
        return Horizontal(
            Input(
                value=name,
                placeholder="Board name",
                id=f"board-name-{idx}",
                classes="board-name-input",
            ),
            Input(
                value=url,
                placeholder="Board URL (https://dev.azure.com/...)",
                id=f"board-url-{idx}",
                classes="board-url-input",
            ),
            Button(
                "✕",
                id=f"remove-board-{idx}",
                classes="board-remove-btn",
                variant="error",
            ),
            id=f"board-row-{idx}",
            classes="board-row",
        )

    # ---- mount: populate from config module globals -----------------------

    def on_mount(self) -> None:
        for key, _label, is_switch in _FIELDS:
            attr_name = _CONFIG_ATTR_MAP[key]
            value = getattr(config, attr_name)
            if is_switch:
                self.query_one(f"#{key}", Switch).value = bool(value)
            else:
                # Lists become comma-separated strings; everything else str()
                if isinstance(value, list):
                    display = ", ".join(str(v) for v in value)
                else:
                    display = str(value)
                self.query_one(f"#{key}", Input).value = display

        boards_list = self.query_one("#boards-list", Vertical)
        boards = config.TRIAGE_BOARD_OPTIONS
        for display_name, url in boards:
            boards_list.mount(self._make_board_row(name=display_name, url=url))

        # Populate investigation selects
        try:
            model_select = self.query_one("#investigation-model-select", Select)
            model_select.value = config.INVESTIGATION_MODEL
        except Exception:
            pass
        try:
            agent_select = self.query_one("#investigation-agent-select", Select)
            agent_select.value = config.INVESTIGATION_AGENT
        except Exception:
            pass
    # ---- save -------------------------------------------------------------

    def action_save(self) -> None:
        """Validate, persist, reload config, and dismiss."""
        data = self._read_form()
        if data is None:
            return  # validation failed — notification already shown
        save_config(data)
        config.load_from_file(data)
        log.info("Settings saved and reloaded.")
        self.dismiss(True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
            return
        if event.button.id == "add-board":
            self.query_one("#boards-list", Vertical).mount(self._make_board_row())
            return
        if event.button.id and event.button.id.startswith("remove-board-"):
            idx = event.button.id.replace("remove-board-", "")
            try:
                row = self.query_one(f"#board-row-{idx}", Horizontal)
                row.remove()
            except Exception:
                log.exception("Failed to remove board row", extra={"row_id": idx})
            return
        if event.button.id == "cancel":
            self.dismiss(False)

    # ---- cancel -----------------------------------------------------------

    def action_cancel(self) -> None:
        self.dismiss(False)

    # ---- form reading / validation ----------------------------------------

    def _read_form(self) -> dict | None:
        """Read all widget values and return a config dict, or None on error."""
        data: dict = {}

        for key, _label, is_switch in _FIELDS:
            if is_switch:
                data[key] = self.query_one(f"#{key}", Switch).value
            else:
                data[key] = self.query_one(f"#{key}", Input).value.strip()

        # --- split ado_projects into a list ---
        raw_projects = data["ado_projects"]
        data["ado_projects"] = [
            p.strip() for p in raw_projects.split(",") if p.strip()
        ]

        # --- collect triage boards from board rows ---
        boards = []
        for row in self.query("#boards-list .board-row"):
            name_input = row.query_one(".board-name-input", Input)
            url_input = row.query_one(".board-url-input", Input)
            name = name_input.value.strip()
            url = url_input.value.strip()
            if name and url:
                boards.append([name, url])
            elif name and not url:
                self.notify(
                    f"Board '{name}' is missing a URL.",
                    severity="error",
                    title="Validation Error",
                )
                url_input.focus()
                return None
            elif url and not name:
                self.notify(
                    "A board URL was provided without a name.",
                    severity="error",
                    title="Validation Error",
                )
                name_input.focus()
                return None
        if not boards:
            # Allow saving with no boards — user can configure them later.
            # The triage tab will be empty until boards are added.
            pass
        data["triage_board_options"] = boards

        # --- read investigation model and agent selects ---
        try:
            model_val = self.query_one("#investigation-model-select", Select).value
            data["investigation_model"] = "" if model_val is Select.BLANK else str(model_val)
        except Exception:
            data["investigation_model"] = ""
        try:
            agent_val = self.query_one("#investigation-agent-select", Select).value
            data["investigation_agent"] = "" if agent_val is Select.BLANK else str(agent_val)
        except Exception:
            data["investigation_agent"] = ""
        # --- parse session_max_age_days as int ---
        raw_age = data["session_max_age_days"]
        try:
            data["session_max_age_days"] = int(raw_age)
        except (ValueError, TypeError):
            self.notify(
                "Session Max Age must be a whole number.",
                severity="error",
                title="Validation Error",
            )
            self.query_one("#session_max_age_days", Input).focus()
            return None

        # --- email is required ---
        if not data["user_email"]:
            self.notify(
                "User Email is required.",
                severity="error",
                title="Validation Error",
            )
            self.query_one("#user_email", Input).focus()
            return None

        return data
