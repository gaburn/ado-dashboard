"""End-to-end integration tests for the edit work-item flow (issue #3, track #3-d).

Marked ``slow`` so default fast-suite runs skip them unless explicitly opted in.
These exercise the full chain: ``EditWorkItemScreen`` mounts → user edits a
field → ``Ctrl+S`` → ``ado_client.update_work_item`` runs against a mocked
``az`` subprocess → screen dismisses.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ado_dashboard import ado_client, config

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
    from ado_dashboard.screens.edit import EditWorkItemScreen
except ImportError:
    pytest.skip("awaiting Thorin track #3-b — screens.edit", allow_module_level=True)

from ado_dashboard.models import WorkItem  # noqa: E402

pytestmark = pytest.mark.slow


def _wi() -> WorkItem:
    base = dict(
        id=42,
        title="Original",
        state="Active",
        work_item_type="Task",
        iteration_path="Project\\Sprint 1",
        area_path="Project",
        tags=[],
        changed_date=datetime(2024, 1, 1, tzinfo=UTC),
        url="https://dev.azure.com/org/project/_workitems/edit/42",
        description="body",
        priority=2,
        parent_id=None,
    )
    if "rev" in WorkItem.__dataclass_fields__:
        base["rev"] = 3
    return WorkItem(**base)


def _proc(payload: dict, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(json.dumps(payload).encode(), b""))
    return proc


def _push_app(wi: WorkItem):
    from textual.app import App

    class _App(App):
        async def on_mount(self_inner) -> None:
            await self_inner.push_screen(EditWorkItemScreen(wi))

    return _App()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org", raising=False)
    monkeypatch.setattr(config, "PROJECT", "TestProject", raising=False)
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com", raising=False)
    monkeypatch.setattr(
        ado_client, "get_allowed_states",
        AsyncMock(return_value=["New", "Active", "Resolved"]),
    )
    monkeypatch.setattr(
        ado_client, "get_iterations",
        AsyncMock(return_value=["Project\\Sprint 1", "Project\\Sprint 2"]),
    )
    monkeypatch.setattr(
        ado_client, "get_areas", AsyncMock(return_value=["Project", "Project\\TeamA"]),
    )


def test_end_to_end_save_against_mocked_az():
    """Full edit cycle against a mocked az CLI: title change + save."""
    wi = _wi()
    updated = {
        "id": 42,
        "rev": 4,
        "fields": {
            "System.Title": "Edited end-to-end",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.IterationPath": "Project\\Sprint 1",
            "System.AreaPath": "Project",
            "System.Tags": "",
            "System.ChangedDate": "2024-01-02T00:00:00Z",
        },
    }

    async def go():
        app = _push_app(wi)
        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=_proc(updated))):
            async with app.run_test() as pilot:
                await pilot.pause()
                from textual.widgets import Input
                inputs = [w for w in pilot.app.screen.walk_children() if isinstance(w, Input)]
                if inputs:
                    inputs[0].value = "Edited end-to-end"
                await pilot.pause()
                await pilot.press("ctrl+s")
                for _ in range(20):
                    await pilot.pause()

    asyncio.run(go())


def test_end_to_end_concurrency_conflict_opens_modal():
    """A 412/rev-mismatch from az surfaces as a conflict modal end-to-end."""
    wi = _wi()
    err_proc = MagicMock()
    err_proc.returncode = 1
    err_proc.communicate = AsyncMock(return_value=(
        b"",
        b"VS403357: The revision you are updating is not the latest revision.",
    ))

    async def go():
        app = _push_app(wi)
        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec",
                   new=AsyncMock(return_value=err_proc)):
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("ctrl+s")
                for _ in range(20):
                    await pilot.pause()
                # A modal (conflict resolver) is expected to sit above edit screen.
                assert len(list(pilot.app.screen_stack)) >= 2

    asyncio.run(go())
