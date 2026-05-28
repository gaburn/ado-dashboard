"""Snapshot tests for ``EditWorkItemScreen`` (issue #3, track #3-d).

These rely on ``pytest-textual-snapshot``. The dependency is not currently in
``pyproject.toml`` (see Glóin), so the suite is skipped at module load until it
ships. Each test renders the screen in a known state at a fixed terminal size
so the SVG snapshot stays stable.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest_textual_snapshot = pytest.importorskip(
    "pytest_textual_snapshot",
    reason="pytest-textual-snapshot not yet in pyproject; pending Glóin add",
)

# Skip if Balin's API or Thorin's screen haven't landed.
from ado_dashboard import ado_client  # noqa: E402

_missing = [
    n
    for n in ("update_work_item", "get_allowed_states", "get_iterations", "get_areas",
              "ConcurrencyError", "ValidationError", "PermissionError")
    if not hasattr(ado_client, n)
]
if _missing:
    pytest.skip(
        f"awaiting Balin track #3-a — missing: {', '.join(_missing)}",
        allow_module_level=True,
    )

try:
    from ado_dashboard.screens.edit import EditWorkItemScreen  # noqa: F401, E402
except ImportError:
    pytest.skip("awaiting Thorin track #3-b — ado_dashboard.screens.edit",
                allow_module_level=True)

from ado_dashboard.models import WorkItem  # noqa: E402

TERMINAL_SIZE = (100, 32)


def _wi(**overrides) -> WorkItem:
    base = dict(
        id=42,
        title="Edit me",
        state="Active",
        work_item_type="Task",
        iteration_path="Project\\Sprint 1",
        area_path="Project\\TeamA",
        tags=[],
        changed_date=datetime(2024, 1, 1, tzinfo=UTC),
        url="https://dev.azure.com/org/project/_workitems/edit/42",
        description="A short body for the snapshot baseline.",
        priority=2,
        parent_id=None,
    )
    base.update(overrides)
    if "rev" in WorkItem.__dataclass_fields__:
        base.setdefault("rev", 3)
    return WorkItem(**base)


def _app_with_screen(wi: WorkItem):
    from ado_dashboard.screens.edit import EditWorkItemScreen
    from textual.app import App

    class _App(App):
        async def on_mount(self_inner) -> None:
            await self_inner.push_screen(EditWorkItemScreen(wi))

    return _App()


# ---------------------------------------------------------------------------
# 1. Initial render — baseline form with all v1 fields populated
# ---------------------------------------------------------------------------
def test_snapshot_initial_render(snap_compare):
    assert snap_compare(_app_with_screen(_wi()), terminal_size=TERMINAL_SIZE)


# ---------------------------------------------------------------------------
# 2. Title cleared — validation banner visible
# ---------------------------------------------------------------------------
def test_snapshot_validation_empty_title(snap_compare):
    async def setup(pilot):
        from textual.widgets import Input

        inputs = [w for w in pilot.app.screen.walk_children() if isinstance(w, Input)]
        if inputs:
            inputs[0].value = ""
        await pilot.pause()

    assert snap_compare(
        _app_with_screen(_wi()),
        terminal_size=TERMINAL_SIZE,
        run_before=setup,
    )


# ---------------------------------------------------------------------------
# 3. Dirty state — title changed, footer suffix visible
# ---------------------------------------------------------------------------
def test_snapshot_dirty_state(snap_compare):
    async def setup(pilot):
        from textual.widgets import Input

        inputs = [w for w in pilot.app.screen.walk_children() if isinstance(w, Input)]
        if inputs:
            inputs[0].value = "Edit me — modified"
        await pilot.pause()

    assert snap_compare(
        _app_with_screen(_wi()),
        terminal_size=TERMINAL_SIZE,
        run_before=setup,
    )


# ---------------------------------------------------------------------------
# 4. Saving — spinner visible
# ---------------------------------------------------------------------------
def test_snapshot_saving_state(snap_compare):
    async def setup(pilot):
        screen = pilot.app.screen
        if hasattr(screen, "_save_state"):
            screen._save_state = "saving"  # type: ignore[attr-defined]
        await pilot.pause()

    assert snap_compare(
        _app_with_screen(_wi()),
        terminal_size=TERMINAL_SIZE,
        run_before=setup,
    )


# ---------------------------------------------------------------------------
# 5. Saved state — success affordance visible
# ---------------------------------------------------------------------------
def test_snapshot_saved_state(snap_compare):
    async def setup(pilot):
        screen = pilot.app.screen
        if hasattr(screen, "_save_state"):
            screen._save_state = "saved"  # type: ignore[attr-defined]
        await pilot.pause()

    assert snap_compare(
        _app_with_screen(_wi()),
        terminal_size=TERMINAL_SIZE,
        run_before=setup,
    )


# ---------------------------------------------------------------------------
# 6. Error state — 5-row error table visible
# ---------------------------------------------------------------------------
def test_snapshot_error_state(snap_compare):
    async def setup(pilot):
        screen = pilot.app.screen
        if hasattr(screen, "_save_state"):
            screen._save_state = "error"  # type: ignore[attr-defined]
        await pilot.pause()

    assert snap_compare(
        _app_with_screen(_wi()),
        terminal_size=TERMINAL_SIZE,
        run_before=setup,
    )


# ---------------------------------------------------------------------------
# 7. Conflict modal — Refresh/Discard prompt
# ---------------------------------------------------------------------------
def test_snapshot_conflict_modal(snap_compare):
    async def setup(pilot):
        screen = pilot.app.screen
        # Best-effort: post a SaveConflicted message if the contract exposes it.
        if hasattr(screen, "SaveConflicted"):
            try:
                screen.post_message(screen.SaveConflicted())  # type: ignore[call-arg]
            except TypeError:
                screen.post_message(screen.SaveConflicted("rev mismatch"))  # type: ignore[call-arg]
        for _ in range(5):
            await pilot.pause()

    assert snap_compare(
        _app_with_screen(_wi()),
        terminal_size=TERMINAL_SIZE,
        run_before=setup,
    )


# ---------------------------------------------------------------------------
# 8. Multi-line description — wraps cleanly
# ---------------------------------------------------------------------------
def test_snapshot_long_description(snap_compare):
    body = "\n".join([f"Line {i} of the description" for i in range(1, 8)])
    assert snap_compare(
        _app_with_screen(_wi(description=body)),
        terminal_size=TERMINAL_SIZE,
    )
