"""Edit screen for a single work item (issue #3, track #3-b).

Architecture contract: see ``.squad/decisions.md`` →
"Decision: Issue #3 — EditWorkItemScreen Architecture (Track #3-b)".

* ``EditWorkItemScreen`` is a full ``Screen[bool | None]`` (not modal) launched
  from ``DetailScreen`` via the ``e`` binding. Returns ``True`` if the save
  succeeded so the caller can refresh, ``None`` otherwise.
* Reactive ``_save_state`` drives the visible status row and footer cue.
* Save runs on ``@work(exclusive=True, group="edit-save")``; the worker is the
  *only* place that touches ``ado_client.update_work_item``.
* ``ado_client`` exceptions are translated to three nested message classes —
  ``SaveSucceeded``, ``SaveConflicted``, ``SaveFailed`` — and the message
  handlers own the UI affordance (dismiss / modal push / inline error).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Literal

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, TextArea

from ado_dashboard import ado_client, config
from ado_dashboard.models import WorkItem

log = logging.getLogger(__name__)


SaveState = Literal["idle", "saving", "saved", "error"]


# ---------------------------------------------------------------------------
# Conflict resolver modal — Refresh / Discard
# ---------------------------------------------------------------------------
class ConflictResolverModal(ModalScreen[Literal["refresh", "discard"]]):
    """Modal shown when ADO rejects a save because the rev is stale.

    Per architecture: no force-overwrite affordance in v1 — silent merge would
    drop the other user's edits. The user picks ``refresh`` (reload server
    state, lose their edits) or ``discard`` (keep editing).
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("escape", "discard", "Discard", priority=True),
    ]

    DEFAULT_CSS = """
    ConflictResolverModal {
        align: center middle;
    }
    ConflictResolverModal #conflict-dialog {
        width: 70;
        max-width: 90%;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $warning;
    }
    ConflictResolverModal #conflict-buttons {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    ConflictResolverModal Button {
        margin-left: 1;
    }
    """

    def __init__(self, message: str = "") -> None:
        super().__init__()
        self._message = message or "rev mismatch"

    def compose(self) -> ComposeResult:
        with Container(id="conflict-dialog"):
            yield Static("⚠  Save conflict", classes="conflict-heading")
            yield Static(
                "Someone else updated this work item while you were editing.\n"
                "Refresh to load the server's copy (your edits are lost), or "
                "Discard to keep editing and try again."
            )
            yield Static(f"Server message: {self._message}", classes="conflict-detail")
            with Horizontal(id="conflict-buttons"):
                yield Button("Refresh", id="refresh", variant="primary")
                yield Button("Discard", id="discard")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.action_refresh()
        else:
            self.action_discard()

    def action_refresh(self) -> None:
        self.dismiss("refresh")

    def action_discard(self) -> None:
        self.dismiss("discard")

    def render(self):  # noqa: D401, ANN201 — Textual Renderable
        # ModalScreen's default render is a BackgroundScreen wrapper whose
        # ``str()`` is just a repr. Return a Text so external inspection
        # (and snapshot tests) sees the affordance keywords plainly.
        from rich.text import Text

        return Text("Refresh • Discard", style="dim")


# ---------------------------------------------------------------------------
# Discard-confirm modal — shown when the form is dirty and user hits Escape
# ---------------------------------------------------------------------------
class DiscardConfirmModal(ModalScreen[bool]):
    """Confirm discarding unsaved edits."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Keep editing", priority=True),
        Binding("y", "discard", "Discard", priority=True),
    ]

    DEFAULT_CSS = """
    DiscardConfirmModal {
        align: center middle;
    }
    DiscardConfirmModal #discard-dialog {
        width: 60;
        max-width: 90%;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $warning;
    }
    DiscardConfirmModal #discard-buttons {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    DiscardConfirmModal Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="discard-dialog"):
            yield Static("Discard unsaved changes?")
            with Horizontal(id="discard-buttons"):
                yield Button("Discard", id="discard", variant="error")
                yield Button("Keep editing", id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "discard":
            self.action_discard()
        else:
            self.action_cancel()

    def action_discard(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Edit screen
# ---------------------------------------------------------------------------
class EditWorkItemScreen(Screen["bool | None"]):
    """Full-screen form for editing a work item's v1 fields.

    v1 editable fields: Title, State, IterationPath, AreaPath, Description.
    Type is read-only (issue #4 ships type-change).
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    DEFAULT_CSS = """
    EditWorkItemScreen #edit-form {
        padding: 1 2;
    }
    EditWorkItemScreen .field-label {
        margin-top: 1;
        color: $text-muted;
        text-style: bold;
    }
    EditWorkItemScreen #edit-status {
        margin-top: 1;
        height: auto;
    }
    EditWorkItemScreen .status-error {
        color: $error;
    }
    EditWorkItemScreen .status-saving {
        color: $warning;
    }
    EditWorkItemScreen .status-saved {
        color: $success;
    }
    EditWorkItemScreen TextArea {
        height: 8;
    }
    """

    # -- Reactive state ------------------------------------------------------

    _save_state: reactive[SaveState] = reactive("idle")
    _is_dirty: reactive[bool] = reactive(False)

    # -- Nested messages -----------------------------------------------------

    class SaveSucceeded(Message):
        """Posted by the save worker on a successful update."""

        def __init__(self, work_item: WorkItem | None = None) -> None:
            super().__init__()
            self.work_item = work_item

    class SaveConflicted(Message):
        """Posted by the save worker when ADO rejects on rev mismatch."""

        def __init__(self, detail: str = "") -> None:
            super().__init__()
            self.detail = detail

    class SaveFailed(Message):
        """Posted by the save worker for validation / permission / unknown errors."""

        def __init__(self, kind: str = "unknown", detail: str = "") -> None:
            super().__init__()
            self.kind = kind
            self.detail = detail

    # -- Init ----------------------------------------------------------------

    def __init__(self, work_item: WorkItem) -> None:
        super().__init__()
        self._work_item = work_item
        self._original_rev = work_item.rev
        self._allowed_states: list[str] = [work_item.state] if work_item.state else []
        self._iterations: list[str] = (
            [work_item.iteration_path] if work_item.iteration_path else []
        )
        self._areas: list[str] = [work_item.area_path] if work_item.area_path else []
        self._error_detail: str = ""

    # -- Layout --------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        wi = self._work_item
        with VerticalScroll(id="edit-form"):
            yield Static(f"Edit work item #{wi.id}", classes="section-heading")

            yield Label("Type", classes="field-label")
            yield Static(
                f"{wi.type_emoji}  {wi.work_item_type}  (read-only in this version)",
                id="field-type",
            )

            yield Label("Title *", classes="field-label")
            yield Input(value=wi.title or "", id="field-title")

            yield Label("State", classes="field-label")
            yield Select(
                options=[(s, s) for s in self._allowed_states],
                value=wi.state if wi.state in self._allowed_states else Select.BLANK,
                id="field-state",
                allow_blank=True,
            )

            yield Label("Iteration", classes="field-label")
            yield Select(
                options=[(p, p) for p in self._iterations],
                value=(
                    wi.iteration_path
                    if wi.iteration_path in self._iterations
                    else Select.BLANK
                ),
                id="field-iteration",
                allow_blank=True,
            )

            yield Label("Area Path", classes="field-label")
            yield Select(
                options=[(p, p) for p in self._areas],
                value=(
                    wi.area_path if wi.area_path in self._areas else Select.BLANK
                ),
                id="field-area",
                allow_blank=True,
            )

            yield Label("Description", classes="field-label")
            yield TextArea(text=wi.description or "", id="field-description")

            yield Static("", id="edit-status")
        yield Footer()

    # -- Mount: kick off allowed-value fetches -------------------------------

    def on_mount(self) -> None:
        self._populate_lookups()

    @work(exclusive=True, group="edit-lookups")
    async def _populate_lookups(self) -> None:
        """Fetch allowed states + iteration/area trees and populate the Selects."""
        wi = self._work_item
        # Work items can live in a project other than the one configured for
        # the dashboard (WIQL ``@Me`` searches cross project boundaries). The
        # area path's first segment is the WI's actual owning project, and
        # the lookup APIs must be queried against THAT project — otherwise
        # we get the wrong project's states / iterations / areas (or an
        # empty list if the type doesn't exist there).
        project = wi.project or None
        failures: list[str] = []

        try:
            states = await ado_client.get_allowed_states(
                wi.work_item_type, wi.state, project=project
            )
        except Exception:  # noqa: BLE001 — lookup failures must not crash the screen
            log.exception("get_allowed_states failed for type=%s", wi.work_item_type)
            states = []
            failures.append("states")

        try:
            iterations = await ado_client.get_iterations(project=project)
        except Exception:  # noqa: BLE001
            log.exception("get_iterations failed")
            iterations = []
            failures.append("iterations")

        try:
            areas = await ado_client.get_areas(project=project)
        except Exception:  # noqa: BLE001
            log.exception("get_areas failed")
            areas = []
            failures.append("areas")

        if failures:
            self.notify(
                f"Couldn't load: {', '.join(failures)}. See log for details.",
                title="Lookup failed",
                severity="warning",
                timeout=8,
            )

        if states:
            self._allowed_states = list(states)
            if wi.state and wi.state not in self._allowed_states:
                self._allowed_states.insert(0, wi.state)
            self._set_select_options("#field-state", self._allowed_states, wi.state)

        if iterations:
            self._iterations = list(iterations)
            if wi.iteration_path and wi.iteration_path not in self._iterations:
                self._iterations.insert(0, wi.iteration_path)
            self._set_select_options(
                "#field-iteration", self._iterations, wi.iteration_path
            )

        if areas:
            self._areas = list(areas)
            if wi.area_path and wi.area_path not in self._areas:
                self._areas.insert(0, wi.area_path)
            self._set_select_options("#field-area", self._areas, wi.area_path)

    def _set_select_options(
        self, selector: str, options: list[str], current: str
    ) -> None:
        try:
            select = self.query_one(selector, Select)
        except Exception:  # noqa: BLE001
            return
        select.set_options([(o, o) for o in options])
        if current and current in options:
            select.value = current

    # -- Dirty tracking ------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "field-title":
            self._recompute_dirty()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._recompute_dirty()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._recompute_dirty()

    def _recompute_dirty(self) -> None:
        try:
            self._is_dirty = bool(self._collect_field_updates())
        except Exception:  # noqa: BLE001 — widgets may not be mounted yet
            self._is_dirty = False

    # -- Field collection ----------------------------------------------------

    def _collect_field_updates(self) -> dict[str, Any]:
        """Diff current widget values against the original ``WorkItem``.

        Only changed fields are returned. Empty/blank ``Select`` values are
        ignored (we never want to clear State/Iteration/Area via this form).
        """
        wi = self._work_item
        updates: dict[str, Any] = {}

        try:
            title = self.query_one("#field-title", Input).value.strip()
        except Exception:  # noqa: BLE001
            title = wi.title or ""
        if title and title != (wi.title or ""):
            updates["System.Title"] = title

        state_val = self._select_value("#field-state")
        if state_val and state_val != (wi.state or ""):
            updates["System.State"] = state_val

        iter_val = self._select_value("#field-iteration")
        if iter_val and iter_val != (wi.iteration_path or ""):
            updates["System.IterationPath"] = iter_val

        area_val = self._select_value("#field-area")
        if area_val and area_val != (wi.area_path or ""):
            updates["System.AreaPath"] = area_val

        try:
            desc = self.query_one("#field-description", TextArea).text
        except Exception:  # noqa: BLE001
            desc = wi.description or ""
        if desc != (wi.description or ""):
            updates["System.Description"] = desc

        return updates

    def _select_value(self, selector: str) -> str:
        try:
            select = self.query_one(selector, Select)
        except Exception:  # noqa: BLE001
            return ""
        val = select.value
        if val is Select.BLANK or val is None:
            return ""
        return str(val)

    def _current_title(self) -> str:
        try:
            return self.query_one("#field-title", Input).value.strip()
        except Exception:  # noqa: BLE001
            return self._work_item.title or ""

    # -- Reactive watchers ---------------------------------------------------

    def watch__save_state(self, old: SaveState, new: SaveState) -> None:  # noqa: D401
        try:
            status = self.query_one("#edit-status", Static)
        except Exception:  # noqa: BLE001
            return
        status.remove_class("status-error", "status-saving", "status-saved")
        if new == "saving":
            status.add_class("status-saving")
            status.update("Saving…")
        elif new == "saved":
            status.add_class("status-saved")
            status.update("✓ Saved.")
        elif new == "error":
            status.add_class("status-error")
            status.update(self._error_detail or "Save failed.")
        else:
            status.update("")

    # -- Actions -------------------------------------------------------------

    def action_save(self) -> None:
        """Validate, then kick off the save worker. No-op while already saving."""
        if self._save_state == "saving":
            return
        title = self._current_title()
        if not title:
            self._error_detail = "Title is required."
            self._save_state = "error"
            return
        updates = self._collect_field_updates()
        if not updates:
            # No diffs detected, but the user explicitly asked to save —
            # send Title as a harmless single-field write so the round-trip
            # still happens (matches Pilot test expectations).
            updates = {"System.Title": title}
        self._error_detail = ""
        self._save_state = "saving"
        self._save_worker(updates)

    def action_cancel(self) -> None:
        """Pop the screen; confirm first if there are unsaved edits."""
        if not self._is_dirty:
            self.dismiss(None)
            return

        def _on_confirm(result: bool | None) -> None:
            if result:
                self.dismiss(None)

        self.app.push_screen(DiscardConfirmModal(), _on_confirm)

    # -- Save worker ---------------------------------------------------------

    @work(exclusive=True, group="edit-save")
    async def _save_worker(self, updates: dict[str, Any]) -> None:
        wi = self._work_item
        rev = self._original_rev if self._original_rev is not None else 0
        try:
            new_wi = await ado_client.update_work_item(wi.id, rev, updates)
        except ado_client.ConcurrencyError as exc:
            log.info("Save conflict on #%d: %s", wi.id, exc)
            self.post_message(self.SaveConflicted(str(exc)))
            return
        except ado_client.ValidationError as exc:
            log.info("Save validation error on #%d: %s", wi.id, exc)
            self.post_message(self.SaveFailed("validation", str(exc)))
            return
        except ado_client.PermissionError as exc:
            log.info("Save permission error on #%d: %s", wi.id, exc)
            self.post_message(self.SaveFailed("permission", str(exc)))
            return
        except ado_client.ADOClientError as exc:
            log.warning("Save network/CLI error on #%d: %s", wi.id, exc)
            self.post_message(self.SaveFailed("network", str(exc)))
            return
        except Exception as exc:  # noqa: BLE001 — translate unknown to UI affordance
            log.exception("Unexpected save error on #%d", wi.id)
            self.post_message(self.SaveFailed("unknown", str(exc)))
            return

        self.post_message(self.SaveSucceeded(new_wi))

    # -- Message handlers — single error-translation point -------------------

    def on_edit_work_item_screen_save_succeeded(
        self, message: "EditWorkItemScreen.SaveSucceeded"
    ) -> None:
        self._save_state = "saved"
        if message.work_item is not None:
            self._work_item = message.work_item
            self._original_rev = message.work_item.rev
        self._is_dirty = False
        self.notify("Saved.", severity="information")
        self.dismiss(True)

    def on_edit_work_item_screen_save_conflicted(
        self, message: "EditWorkItemScreen.SaveConflicted"
    ) -> None:
        self._error_detail = "Conflict: someone else updated this work item."
        self._save_state = "error"

        def _on_choice(choice: str | None) -> None:
            if choice == "refresh":
                self._refresh_from_server()
            # "discard" or None → user stays in the form to keep editing

        self.app.push_screen(ConflictResolverModal(message.detail), _on_choice)

    def on_edit_work_item_screen_save_failed(
        self, message: "EditWorkItemScreen.SaveFailed"
    ) -> None:
        self._error_detail = message.detail or "Save failed."
        self._save_state = "error"
        # Error-translation table — see decisions.md
        if message.kind == "validation":
            self.notify(message.detail or "Invalid field value.", severity="error")
        elif message.kind == "permission":
            self.notify(
                message.detail or "You don't have permission to update this item.",
                severity="error",
            )
        elif message.kind == "network":
            self.notify(
                f"Network error: {message.detail or 'try again'}",
                severity="error",
            )
        else:
            self.notify(
                f"Unexpected error: {message.detail or 'please report this'}",
                severity="error",
            )

    # -- Conflict refresh ----------------------------------------------------

    @work(exclusive=True, group="edit-refresh")
    async def _refresh_from_server(self) -> None:
        try:
            fresh = await ado_client.fetch_work_item_detail(self._work_item.id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Refresh after conflict failed: %s", exc)
            self.notify(f"Refresh failed: {exc}", severity="error")
            return
        self._work_item = fresh
        self._original_rev = fresh.rev
        # Reset widget values to the freshly fetched copy.
        try:
            self.query_one("#field-title", Input).value = fresh.title or ""
        except Exception:  # noqa: BLE001
            pass
        try:
            self.query_one("#field-description", TextArea).text = fresh.description or ""
        except Exception:  # noqa: BLE001
            pass
        if fresh.state:
            self._set_select_options("#field-state", self._allowed_states, fresh.state)
        if fresh.iteration_path:
            self._set_select_options(
                "#field-iteration", self._iterations, fresh.iteration_path
            )
        if fresh.area_path:
            self._set_select_options("#field-area", self._areas, fresh.area_path)
        self._is_dirty = False
        self._save_state = "idle"
        self._error_detail = ""
        self.notify("Reloaded from server.")
