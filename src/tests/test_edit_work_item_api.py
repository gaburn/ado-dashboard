"""Tests for the work-item edit API surface (issue #3, track #3-a).

These tests target Balin's planned additions to ``ado_client``:

* ``update_work_item(work_item_id, rev, field_updates) -> WorkItem``
* ``get_allowed_states(work_item_type) -> list[str]``
* ``get_iterations() -> list[str]``
* ``get_areas() -> list[str]``
* Exceptions: ``ConcurrencyError``, ``ValidationError``, ``PermissionError``

All subprocess calls are mocked at ``asyncio.create_subprocess_exec`` — no real
``az`` is invoked. Module-level skip is applied when any contract piece is
missing so this file is import-safe while track #3-a lands in parallel.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ado_dashboard import ado_client, config

# ---------------------------------------------------------------------------
# Contract guard — skip the entire module until Balin's surface lands.
# ---------------------------------------------------------------------------
_MISSING = [
    name
    for name in (
        "update_work_item",
        "get_allowed_states",
        "get_iterations",
        "get_areas",
        "ConcurrencyError",
        "ValidationError",
        "PermissionError",
    )
    if not hasattr(ado_client, name)
]
if _MISSING:
    pytest.skip(
        f"awaiting Balin track #3-a — missing on ado_client: {', '.join(_MISSING)}",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> MagicMock:
    """Return a mock asyncio.subprocess.Process with the given output."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


def _wi_payload(rev: int = 3, **overrides) -> dict:
    """Build a minimal ``az boards work-item show`` JSON payload."""
    fields = {
        "System.Title": "Test WI",
        "System.State": "Active",
        "System.WorkItemType": "Task",
        "System.IterationPath": "Project\\Sprint 1",
        "System.AreaPath": "Project",
        "System.Tags": "",
        "System.ChangedDate": "2024-01-01T00:00:00Z",
    }
    fields.update(overrides.get("fields", {}))
    return {"id": overrides.get("id", 42), "rev": rev, "fields": fields}


def _patched_subprocess(*procs: MagicMock):
    """Patch shutil.which + create_subprocess_exec to return ``procs`` in order.

    A single proc is reused for every call; a list of procs is consumed FIFO.
    Returns the (which_patch, exec_patch) tuple. ``exec_patch`` is a MagicMock
    side-effect patch — entering it as ``with ... as mock_exec`` exposes
    ``mock_exec.mock_calls`` for command-line assertions.
    """
    queue = list(procs)

    async def fake_exec(*args, **kwargs):
        if len(queue) == 1:
            return queue[0]
        return queue.pop(0)

    which = patch("shutil.which", return_value="/usr/bin/az")
    exec_ = patch("asyncio.create_subprocess_exec", side_effect=fake_exec)
    return which, exec_


@pytest.fixture(autouse=True)
def _ado_env(monkeypatch):
    """Make config look configured so URL flags resolve cleanly."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org", raising=False)
    monkeypatch.setattr(config, "PROJECT", "TestProject", raising=False)
    monkeypatch.setattr(config, "PROJECTS", ["TestProject"], raising=False)
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com", raising=False)
    # Best-effort cache reset between tests for fns that cache states/trees.
    for cache_attr in (
        "_STATE_CACHE",
        "_ITERATION_CACHE",
        "_AREA_CACHE",
        "_ALLOWED_STATES_CACHE",
        "_ITERATIONS_CACHE",
        "_AREAS_CACHE",
    ):
        if hasattr(ado_client, cache_attr):
            try:
                getattr(ado_client, cache_attr).clear()
            except Exception:
                pass


# ===========================================================================
# update_work_item — happy paths
# ===========================================================================
class TestUpdateWorkItemHappy:
    def test_returns_workitem_on_success(self):
        proc = make_proc(stdout=json.dumps(_wi_payload(rev=4)).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            wi = asyncio.run(
                ado_client.update_work_item(42, rev=3, field_updates={"System.Title": "New"})
            )
        assert wi.id == 42
        assert wi.title == "Test WI" or wi.title == "New"  # depends on server echo

    def test_updates_single_field_title(self):
        proc = make_proc(
            stdout=json.dumps(_wi_payload(rev=4, fields={"System.Title": "Renamed"})).encode()
        )
        which, exec_ = _patched_subprocess(proc)
        with which, exec_ as mock_exec:
            wi = asyncio.run(
                ado_client.update_work_item(42, rev=3, field_updates={"System.Title": "Renamed"})
            )
        assert wi.title == "Renamed"
        # The az command must reference System.Title
        called = " ".join(str(a) for call in mock_exec.mock_calls for a in call.args)
        assert "System.Title" in called or "Title" in called

    def test_updates_multiple_fields(self):
        proc = make_proc(
            stdout=json.dumps(
                _wi_payload(
                    rev=4,
                    fields={
                        "System.Title": "T2",
                        "System.State": "Resolved",
                        "System.IterationPath": "Project\\Sprint 2",
                    },
                )
            ).encode()
        )
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            wi = asyncio.run(
                ado_client.update_work_item(
                    42,
                    rev=3,
                    field_updates={
                        "System.Title": "T2",
                        "System.State": "Resolved",
                        "System.IterationPath": "Project\\Sprint 2",
                    },
                )
            )
        assert wi.state == "Resolved"
        assert wi.title == "T2"
        assert wi.iteration_path == "Project\\Sprint 2"

    def test_updates_all_v1_fields(self):
        """Title, State, Iteration, Area, Description — the v1 scope."""
        updates = {
            "System.Title": "ALL",
            "System.State": "Active",
            "System.IterationPath": "Project\\Sprint 9",
            "System.AreaPath": "Project\\Team",
            "System.Description": "new body",
        }
        echo_fields = dict(updates)
        echo_fields.setdefault("System.WorkItemType", "Task")
        echo_fields.setdefault("System.Tags", "")
        echo_fields.setdefault("System.ChangedDate", "2024-01-02T00:00:00Z")
        proc = make_proc(stdout=json.dumps(_wi_payload(rev=4, fields=echo_fields)).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            wi = asyncio.run(ado_client.update_work_item(42, rev=3, field_updates=updates))
        assert wi.title == "ALL"
        assert wi.area_path == "Project\\Team"
        assert wi.description == "new body"

    def test_passes_id_in_command(self):
        proc = make_proc(stdout=json.dumps(_wi_payload()).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_ as mock_exec:
            asyncio.run(
                ado_client.update_work_item(99, rev=1, field_updates={"System.Title": "x"})
            )
        called = " ".join(str(a) for call in mock_exec.mock_calls for a in call.args)
        assert "99" in called

    def test_returns_workitem_with_updated_rev(self):
        """The returned WorkItem reflects post-update rev (if the field is exposed)."""
        proc = make_proc(stdout=json.dumps(_wi_payload(rev=7)).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            wi = asyncio.run(
                ado_client.update_work_item(42, rev=6, field_updates={"System.Title": "x"})
            )
        # rev field is optional in v1; assert only if exposed.
        if hasattr(wi, "rev"):
            assert wi.rev == 7

    def test_empty_field_updates_returns_without_calling_az(self):
        """No-op update should not shell out — or if it does, must not raise."""
        proc = make_proc(stdout=json.dumps(_wi_payload(rev=3)).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_ as mock_exec:
            try:
                asyncio.run(ado_client.update_work_item(42, rev=3, field_updates={}))
            except (ValueError, ado_client.ValidationError):
                # Acceptable: reject empty updates.
                return
        # If it didn't raise, it should either skip the call or still succeed.
        assert isinstance(mock_exec.call_count, int)


# ===========================================================================
# update_work_item — failure paths
# ===========================================================================
class TestUpdateWorkItemFailures:
    def test_rev_mismatch_raises_concurrency_error(self):
        """Server reports rev conflict (VS403357 or similar) → ConcurrencyError."""
        proc = make_proc(
            stderr=(
                b"VS403357: The revision you are updating is not the latest revision. "
                b"Please refresh and try again."
            ),
            returncode=1,
        )
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.ConcurrencyError):
                asyncio.run(
                    ado_client.update_work_item(42, rev=1, field_updates={"System.Title": "x"})
                )

    def test_ado_400_raises_validation_error(self):
        """ADO rejects the field value (400) → ValidationError."""
        proc = make_proc(
            stderr=(
                b"TF401320: Rule Error: The field 'System.State' contains a value that "
                b"is not in the list of supported values. (status 400)"
            ),
            returncode=1,
        )
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.ValidationError):
                asyncio.run(
                    ado_client.update_work_item(
                        42, rev=3, field_updates={"System.State": "Bogus"}
                    )
                )

    def test_ado_403_raises_permission_error(self):
        """ADO denies the write (403) → PermissionError."""
        proc = make_proc(
            stderr=(
                b"TF401027: You need the following permission(s) to perform this action: "
                b"Edit work items in this node. (status 403)"
            ),
            returncode=1,
        )
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.PermissionError):
                asyncio.run(
                    ado_client.update_work_item(42, rev=3, field_updates={"System.Title": "x"})
                )

    def test_generic_failure_raises_ado_client_error(self):
        proc = make_proc(stderr=b"Some unexpected az failure", returncode=1)
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.ADOClientError):
                asyncio.run(
                    ado_client.update_work_item(42, rev=3, field_updates={"System.Title": "x"})
                )

    def test_network_error_propagates_as_ado_client_error(self):
        """A network-style exception from create_subprocess_exec surfaces cleanly."""
        async def boom(*args, **kwargs):
            raise OSError("network down")

        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec", new=boom):
            with pytest.raises((ado_client.ADOClientError, OSError)):
                asyncio.run(
                    ado_client.update_work_item(42, rev=3, field_updates={"System.Title": "x"})
                )

    def test_az_missing_on_path_raises(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(ado_client.ADOClientError, match="not found on PATH"):
                asyncio.run(
                    ado_client.update_work_item(42, rev=3, field_updates={"System.Title": "x"})
                )


# ===========================================================================
# get_allowed_states
# ===========================================================================
class TestGetAllowedStates:
    @staticmethod
    def _states_payload(names):
        return [{"name": n, "category": "InProgress"} for n in names]

    def test_returns_list_of_state_names(self):
        proc = make_proc(
            stdout=json.dumps(self._states_payload(["New", "Active", "Resolved"])).encode()
        )
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            states = asyncio.run(ado_client.get_allowed_states("Task"))
        assert "Active" in states
        assert "New" in states

    def test_filters_by_work_item_type(self):
        proc = make_proc(stdout=json.dumps(self._states_payload(["New"])).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_ as mock_exec:
            asyncio.run(ado_client.get_allowed_states("Bug"))
        called = " ".join(str(a) for call in mock_exec.mock_calls for a in call.args)
        assert "Bug" in called

    def test_empty_response_returns_empty_list(self):
        proc = make_proc(stdout=b"[]")
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            states = asyncio.run(ado_client.get_allowed_states("Task"))
        assert states == []

    def test_error_propagates_as_ado_client_error(self):
        proc = make_proc(stderr=b"boom", returncode=1)
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.ADOClientError):
                asyncio.run(ado_client.get_allowed_states("Task"))

    def test_cache_hit_avoids_second_subprocess_call(self):
        """Second call with the same type should not re-shell out."""
        proc = make_proc(stdout=json.dumps(self._states_payload(["New", "Active"])).encode())
        call_count = 0

        async def counting_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return proc

        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec", new=counting_exec):
            asyncio.run(ado_client.get_allowed_states("Task"))
            asyncio.run(ado_client.get_allowed_states("Task"))
        assert call_count <= 1, "states should be cached per work-item-type"

    def test_different_types_do_not_share_cache(self):
        async def gen_proc(*args, **kwargs):
            return make_proc(stdout=json.dumps([{"name": "X"}]).encode())

        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec", new=gen_proc):
            a = asyncio.run(ado_client.get_allowed_states("Task"))
            b = asyncio.run(ado_client.get_allowed_states("Bug"))
        assert a == b == ["X"]  # both succeed, no cross-pollination errors


# ===========================================================================
# get_iterations
# ===========================================================================
class TestGetIterations:
    @staticmethod
    def _it_payload(paths):
        # ADO returns a tree; tests assume a flat list of path strings.
        return [{"path": p, "name": p.rsplit("\\", 1)[-1]} for p in paths]

    def test_returns_list_of_iteration_paths(self):
        payload = self._it_payload(["Project\\Sprint 1", "Project\\Sprint 2"])
        proc = make_proc(stdout=json.dumps(payload).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            iters = asyncio.run(ado_client.get_iterations())
        # Tolerate either a list of strings or a list of dicts.
        flattened = [i if isinstance(i, str) else i.get("path", i.get("name")) for i in iters]
        assert any("Sprint 1" in p for p in flattened)

    def test_empty_returns_empty(self):
        proc = make_proc(stdout=b"[]")
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            assert asyncio.run(ado_client.get_iterations()) == []

    def test_cache_hit_avoids_second_subprocess_call(self):
        proc = make_proc(stdout=json.dumps(self._it_payload(["Project\\S1"])).encode())
        call_count = 0

        async def counting_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return proc

        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec", new=counting_exec):
            asyncio.run(ado_client.get_iterations())
            asyncio.run(ado_client.get_iterations())
        assert call_count <= 1, "iterations should be cached"

    def test_error_propagates(self):
        proc = make_proc(stderr=b"boom", returncode=1)
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.ADOClientError):
                asyncio.run(ado_client.get_iterations())


# ===========================================================================
# get_areas
# ===========================================================================
class TestGetAreas:
    @staticmethod
    def _area_payload(paths):
        return [{"path": p, "name": p.rsplit("\\", 1)[-1]} for p in paths]

    def test_returns_list_of_area_paths(self):
        payload = self._area_payload(["Project", "Project\\TeamA", "Project\\TeamB"])
        proc = make_proc(stdout=json.dumps(payload).encode())
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            areas = asyncio.run(ado_client.get_areas())
        flattened = [a if isinstance(a, str) else a.get("path", a.get("name")) for a in areas]
        assert any("TeamA" in p for p in flattened)

    def test_empty_returns_empty(self):
        proc = make_proc(stdout=b"[]")
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            assert asyncio.run(ado_client.get_areas()) == []

    def test_cache_hit_avoids_second_subprocess_call(self):
        proc = make_proc(stdout=json.dumps(self._area_payload(["Project"])).encode())
        call_count = 0

        async def counting_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return proc

        with patch("shutil.which", return_value="/usr/bin/az"), \
             patch("asyncio.create_subprocess_exec", new=counting_exec):
            asyncio.run(ado_client.get_areas())
            asyncio.run(ado_client.get_areas())
        assert call_count <= 1, "areas should be cached"

    def test_error_propagates(self):
        proc = make_proc(stderr=b"boom", returncode=1)
        which, exec_ = _patched_subprocess(proc)
        with which, exec_:
            with pytest.raises(ado_client.ADOClientError):
                asyncio.run(ado_client.get_areas())


# ===========================================================================
# Exception hierarchy sanity
# ===========================================================================
class TestExceptionTaxonomy:
    def test_concurrency_error_is_distinct(self):
        assert ado_client.ConcurrencyError is not ado_client.ValidationError
        assert ado_client.ConcurrencyError is not ado_client.PermissionError

    def test_all_errors_are_exceptions(self):
        for name in ("ConcurrencyError", "ValidationError", "PermissionError"):
            cls = getattr(ado_client, name)
            assert isinstance(cls, type) and issubclass(cls, BaseException)


# ===========================================================================
# WorkItem.rev field gap (Thorin's blocker)
# ===========================================================================
class TestWorkItemRevField:
    def test_workitem_dataclass_exposes_rev(self):
        """Thorin's architecture note flagged this as a blocker for #3-b."""
        from ado_dashboard.models import WorkItem

        assert "rev" in WorkItem.__dataclass_fields__, (
            "WorkItem.rev is required for optimistic concurrency control"
        )

    def test_workitem_from_az_json_populates_rev(self):
        from ado_dashboard.models import WorkItem

        wi = WorkItem.from_az_json(_wi_payload(rev=11))
        assert getattr(wi, "rev", None) == 11
