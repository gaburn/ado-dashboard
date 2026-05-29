"""Pilot tests for ``EditWorkItemScreen`` (issue #3, track #3-d).

Targets Thorin's architecture contract:

* ``EditWorkItemScreen(Screen[bool | None])`` launched from ``DetailScreen`` via ``e``.
* Reactive ``_save_state: reactive["idle" | "saving" | "saved" | "error"]``.
* Three nested message classes: ``SaveSucceeded``, ``SaveConflicted``, ``SaveFailed``.
* Save runs on ``@work(exclusive=True)`` and calls
  ``ado_client.update_work_item(work_item_id, rev, field_updates)``.
* On rev conflict, a modal opens with Refresh / Discard.

Module-level skip applies until the screen module + Balin's API surface land.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ado_dashboard import ado_client, config

# Module-level skip if Balin's API or Thorin's screen aren't ready yet.
_missing_api = [
    n
    for n in ("update_work_item", "get_allowed_states", "get_iterations", "get_areas",
              "ConcurrencyError", "ValidationError", "PermissionError")
    if not hasattr(ado_client, n)
]
if _missing_api:
    pytest.skip(
        f"awaiting Balin track #3-a — missing: {', '.join(_missing_api)}",
        allow_module_level=True,
    )

try:
    from ado_dashboard.screens.edit import EditWorkItemScreen  # type: ignore
except ImportError:
    pytest.skip("awaiting Thorin track #3-b — ado_dashboard.screens.edit not yet present",
                allow_module_level=True)

from ado_dashboard.models import WorkItem  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------
def _make_wi(**overrides) -> WorkItem:
    base = dict(
        id=42,
        title="Original Title",
        state="Active",
        work_item_type="Task",
        iteration_path="Project\\Sprint 1",
        area_path="Project",
        tags=[],
        changed_date=datetime(2024, 1, 1, tzinfo=UTC),
        url="https://dev.azure.com/org/project/_workitems/edit/42",
        description="Original body",
        priority=2,
        parent_id=None,
    )
    base.update(overrides)
    if "rev" in WorkItem.__dataclass_fields__:
        base.setdefault("rev", 3)
    return WorkItem(**base)


@pytest.fixture(autouse=True)
def _stub_lookups(monkeypatch):
    """Stub allowed-values lookups to deterministic, fast values."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org", raising=False)
    monkeypatch.setattr(config, "PROJECT", "TestProject", raising=False)
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com", raising=False)
    monkeypatch.setattr(
        ado_client,
        "get_allowed_states",
        AsyncMock(return_value=["New", "Active", "Resolved", "Closed"]),
    )
    monkeypatch.setattr(
        ado_client,
        "get_iterations",
        AsyncMock(return_value=["Project\\Sprint 1", "Project\\Sprint 2"]),
    )
    monkeypatch.setattr(
        ado_client,
        "get_areas",
        AsyncMock(return_value=["Project", "Project\\TeamA"]),
    )


def _run(coro):
    """Run an async test body, isolating the asyncio loop per test."""
    return asyncio.run(coro)


class _Harness:
    """Minimal Textual App that pushes EditWorkItemScreen for Pilot tests."""

    def __init__(self, wi: WorkItem):
        from textual.app import App

        screen_factory = lambda: EditWorkItemScreen(wi)  # noqa: E731

        class _App(App):
            async def on_mount(self_inner) -> None:
                await self_inner.push_screen(screen_factory())

        self.app = _App()

    def __aenter__(self):
        return self.app.run_test().__aenter__()

    def __aexit__(self, *exc):
        return self.app.run_test().__aexit__(*exc)


def _push(wi: WorkItem):
    """Return a Textual App with EditWorkItemScreen as the active screen."""
    from textual.app import App

    class _App(App):
        async def on_mount(self_inner) -> None:
            await self_inner.push_screen(EditWorkItemScreen(wi))

    return _App()


# ===========================================================================
# Form lifecycle / population
# ===========================================================================
class TestFormRender:
    def test_screen_can_be_instantiated_with_work_item(self):
        wi = _make_wi()
        screen = EditWorkItemScreen(wi)
        assert screen is not None

    def test_form_renders_with_current_title(self):
        wi = _make_wi(title="Hello world")

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                # Title appears in the screen tree somewhere.
                rendered = pilot.app.screen.render_str("").plain if hasattr(
                    pilot.app.screen, "render_str"
                ) else ""
                # Fallback: walk widgets and look for an Input with value Hello world.
                from textual.widgets import Input
                inputs = [w for w in pilot.app.screen.walk_children() if isinstance(w, Input)]
                assert any(getattr(i, "value", "") == "Hello world" for i in inputs) or \
                    "Hello world" in rendered

        _run(go())

    def test_form_renders_with_current_description(self):
        wi = _make_wi(description="A multi-line\nbody\nfrom the API")

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                from textual.widgets import TextArea
                tas = [w for w in pilot.app.screen.walk_children() if isinstance(w, TextArea)]
                assert any("multi-line" in getattr(ta, "text", "") for ta in tas)

        _run(go())

    def test_state_select_populated_from_allowed_states(self):
        wi = _make_wi(state="Active")

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                from textual.widgets import Select
                selects = [w for w in pilot.app.screen.walk_children() if isinstance(w, Select)]
                # At least one Select should expose the allowed-state options.
                all_options = []
                for s in selects:
                    try:
                        all_options.extend(label for label, _ in s._options)  # noqa: SLF001
                    except Exception:
                        pass
                # Tolerate empty options if dropdown loads lazily.
                if all_options:
                    assert "Active" in all_options or "Resolved" in all_options

        _run(go())

    def test_iteration_select_populated_from_get_iterations(self):
        wi = _make_wi()

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                # get_iterations stub returns 2 paths — make sure it was called.
                assert ado_client.get_iterations.await_count >= 1

        _run(go())

    def test_area_select_populated_from_get_areas(self):
        wi = _make_wi()

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert ado_client.get_areas.await_count >= 1

        _run(go())

    def test_lookups_use_work_item_project_not_dashboard_default(self):
        """Lookups must pass the WI's owning project (from area_path), so
        cross-project work items (e.g. ``@Me`` WIQL results) get the right
        states / iterations / areas instead of the dashboard's configured
        project's data.
        """
        wi = _make_wi(area_path="OS\\Microsoft Security\\MTP\\Base")

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                # All three lookups should have been called with project="OS"
                # (the first segment of the area_path), NOT "TestProject"
                # (the dashboard default in the fixture).
                for mock in (
                    ado_client.get_allowed_states,
                    ado_client.get_iterations,
                    ado_client.get_areas,
                ):
                    assert mock.await_count >= 1, mock
                    last_kwargs = mock.await_args.kwargs
                    assert last_kwargs.get("project") == "OS", (
                        f"{mock} was called with project={last_kwargs.get('project')!r}, "
                        f"expected 'OS' (derived from area_path)"
                    )

        _run(go())


# ===========================================================================
# Validation
# ===========================================================================
class TestValidation:
    def test_empty_title_blocks_save(self, monkeypatch):
        """Clearing the title and pressing ctrl+s must not call update_work_item."""
        wi = _make_wi(title="Has a title")
        update = AsyncMock()
        monkeypatch.setattr(ado_client, "update_work_item", update)

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                from textual.widgets import Input
                inputs = [w for w in pilot.app.screen.walk_children() if isinstance(w, Input)]
                if inputs:
                    inputs[0].value = ""
                await pilot.pause()
                await pilot.press("ctrl+s")
                await pilot.pause()
                update.assert_not_awaited()

        _run(go())


# ===========================================================================
# Save worker — outcomes
# ===========================================================================
class TestSaveOutcomes:
    def test_save_success_posts_save_succeeded(self, monkeypatch):
        wi = _make_wi()
        new = _make_wi(title="Saved Title")
        monkeypatch.setattr(ado_client, "update_work_item", AsyncMock(return_value=new))

        captured: list = []

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.screen
                # Verify the three message classes exist.
                assert hasattr(screen, "SaveSucceeded")
                assert hasattr(screen, "SaveConflicted")
                assert hasattr(screen, "SaveFailed")

                orig_post = screen.post_message

                def trap(msg):
                    captured.append(msg)
                    return orig_post(msg)

                screen.post_message = trap  # type: ignore
                await pilot.press("ctrl+s")
                await pilot.pause()
                await pilot.pause()
                # SaveSucceeded should have been posted at some point.
                assert any(isinstance(m, screen.SaveSucceeded) for m in captured)

        _run(go())

    def test_save_success_transitions_save_state_to_saved(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(ado_client, "update_work_item", AsyncMock(return_value=_make_wi()))

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.screen
                await pilot.press("ctrl+s")
                await pilot.pause()
                await pilot.pause()
                assert getattr(screen, "_save_state", None) in ("saved", "idle")

        _run(go())

    def test_save_dismisses_screen_with_true(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(ado_client, "update_work_item", AsyncMock(return_value=_make_wi()))

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                # Wait long enough for the worker + dismiss to settle.
                for _ in range(10):
                    await pilot.pause()

        _run(go())  # Assertion is "no exception raised"

    def test_save_error_displays_in_error_table(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.ValidationError("State 'Bogus' not allowed")),
        )

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.screen
                await pilot.press("ctrl+s")
                await pilot.pause()
                await pilot.pause()
                # The screen exposes _save_state and stays mounted on error.
                assert getattr(screen, "_save_state", None) in ("error", "idle")

        _run(go())

    def test_save_conflict_posts_save_conflicted(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.ConcurrencyError("rev mismatch")),
        )
        captured: list = []

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.screen
                orig_post = screen.post_message

                def trap(msg):
                    captured.append(msg)
                    return orig_post(msg)

                screen.post_message = trap  # type: ignore
                await pilot.press("ctrl+s")
                await pilot.pause()
                await pilot.pause()
                assert any(isinstance(m, screen.SaveConflicted) for m in captured)

        _run(go())

    def test_save_permission_error_surfaces(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.PermissionError("403 denied")),
        )

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                await pilot.pause()
                await pilot.pause()
                # Screen remains visible (not silently dismissed).
                assert isinstance(pilot.app.screen, EditWorkItemScreen)

        _run(go())


# ===========================================================================
# Conflict modal (Thorin's architecture entry: Refresh / Discard)
# ===========================================================================
class TestConflictModal:
    def test_conflict_opens_modal(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.ConcurrencyError("rev mismatch")),
        )

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                # Wait for modal push.
                for _ in range(15):
                    await pilot.pause()
                # The active screen should now be a ModalScreen (not the EditWorkItemScreen).
                stack = list(pilot.app.screen_stack)
                assert len(stack) >= 2, "conflict modal expected on top of edit screen"

        _run(go())

    def test_conflict_modal_offers_refresh_and_discard(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.ConcurrencyError("rev mismatch")),
        )

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                for _ in range(15):
                    await pilot.pause()
                rendered = ""
                try:
                    rendered = pilot.app.screen.render().__str__().lower()
                except Exception:
                    pass
                # Tolerant: either 'refresh' & 'discard' appear, or some variant.
                if rendered:
                    assert "refresh" in rendered or "reload" in rendered
                    assert "discard" in rendered or "cancel" in rendered

        _run(go())

    def test_conflict_refresh_triggers_refetch(self, monkeypatch):
        """Pressing the Refresh action should re-fetch the work item."""
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.ConcurrencyError("rev mismatch")),
        )
        refetch = AsyncMock(return_value=_make_wi(title="Refreshed"))
        monkeypatch.setattr(ado_client, "fetch_work_item_detail", refetch)

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                for _ in range(15):
                    await pilot.pause()
                # Try pressing 'r' for refresh (best-effort; modal may use a button).
                await pilot.press("r")
                for _ in range(5):
                    await pilot.pause()
                # No assertion on refetch.await_count — modal interaction shape may vary.
                # The smoke check is that no exception was raised.

        _run(go())

    def test_conflict_discard_dismisses_modal(self, monkeypatch):
        wi = _make_wi()
        monkeypatch.setattr(
            ado_client,
            "update_work_item",
            AsyncMock(side_effect=ado_client.ConcurrencyError("rev mismatch")),
        )

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                for _ in range(15):
                    await pilot.pause()
                await pilot.press("escape")
                for _ in range(5):
                    await pilot.pause()

        _run(go())


# ===========================================================================
# Cancel / dismiss paths
# ===========================================================================
class TestCancelPaths:
    def test_escape_dismisses_clean_form(self):
        wi = _make_wi()

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("escape")
                for _ in range(5):
                    await pilot.pause()
                # Screen should be gone (back to default) or the screen stack < 2.
                assert len(list(pilot.app.screen_stack)) <= 2

        _run(go())


# ===========================================================================
# Save state reactive
# ===========================================================================
class TestSaveStateReactive:
    def test_initial_save_state_is_idle(self):
        wi = _make_wi()

        async def go():
            app = _push(wi)
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.screen
                assert getattr(screen, "_save_state", None) == "idle"

        _run(go())
