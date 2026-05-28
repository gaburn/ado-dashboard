"""Tests for ado_dashboard.ado_client — full coverage of the az CLI data layer.

All subprocess calls are mocked at asyncio.create_subprocess_exec so no real
``az`` binary is invoked during the test run.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ado_dashboard import ado_client, config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> MagicMock:
    """Return a mock asyncio.subprocess.Process with the given output."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


_MINIMAL_PR: dict = {
    "pullRequestId": 42,
    "title": "Test PR",
    "status": "active",
    "isDraft": False,
    "createdBy": {"displayName": "Author", "uniqueName": "author@example.com"},
    "repository": {"name": "TestRepo", "project": {"name": "TestProject"}},
    "sourceRefName": "refs/heads/feature",
    "targetRefName": "refs/heads/main",
    "creationDate": "2024-01-01T00:00:00Z",
    "reviewers": [],
    "labels": [],
}

_MINIMAL_WI: dict = {
    "id": 99,
    "fields": {
        "System.Title": "Test Work Item",
        "System.State": "Active",
        "System.WorkItemType": "Task",
        "System.IterationPath": "Project\\Sprint 1",
        "System.AreaPath": "Project",
        "System.Tags": "",
        "System.ChangedDate": "2024-01-01T00:00:00Z",
    },
}


# ---------------------------------------------------------------------------
# _run_az — success paths
# ---------------------------------------------------------------------------

def test_run_az_returns_dict_on_success():
    """_run_az returns parsed dict when az exits 0 with a JSON object."""
    payload = {"pullRequestId": 1}
    proc = make_proc(stdout=json.dumps(payload).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        result = asyncio.run(ado_client._run_az(["repos", "pr", "show", "--id", "1"]))
    assert result == payload


def test_run_az_returns_list_on_success():
    """_run_az returns parsed list when az exits 0 with a JSON array."""
    payload = [{"id": 1}, {"id": 2}]
    proc = make_proc(stdout=json.dumps(payload).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        result = asyncio.run(ado_client._run_az(["boards", "query"]))
    assert result == payload


def test_run_az_empty_stdout_returns_empty_list():
    """_run_az returns [] when az exits 0 but stdout is empty (no results)."""
    proc = make_proc(stdout=b"")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        result = asyncio.run(ado_client._run_az(["repos", "pr", "list"]))
    assert result == []


def test_run_az_whitespace_stdout_returns_empty_list():
    """_run_az strips whitespace and returns [] when stdout is only whitespace."""
    proc = make_proc(stdout=b"   \n  ")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        result = asyncio.run(ado_client._run_az(["boards", "query"]))
    assert result == []


# ---------------------------------------------------------------------------
# _run_az — failure paths
# ---------------------------------------------------------------------------

def test_run_az_raises_when_az_not_on_path():
    """_run_az raises ADOClientError immediately when az is absent from PATH."""
    with patch("shutil.which", return_value=None):
        with pytest.raises(ado_client.ADOClientError, match="not found on PATH"):
            asyncio.run(ado_client._run_az(["repos", "pr", "list"]))


def test_run_az_raises_on_nonzero_exit():
    """_run_az raises ADOClientError when az exits with non-zero code."""
    proc = make_proc(stderr=b"Some CLI error", returncode=1)
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        with pytest.raises(ado_client.ADOClientError):
            asyncio.run(ado_client._run_az(["repos", "pr", "list"]))


def test_run_az_raises_on_malformed_json():
    """_run_az raises ADOClientError when stdout is not parseable JSON."""
    proc = make_proc(stdout=b"not-json{{{")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        with pytest.raises(ado_client.ADOClientError, match="parse az CLI JSON"):
            asyncio.run(ado_client._run_az(["repos", "pr", "list"]))


def test_run_az_passes_output_json_flag():
    """_run_az appends --output json to the az command."""
    proc = make_proc(stdout=b"[]")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)) as mock_exec:
        asyncio.run(ado_client._run_az(["repos", "pr", "list"]))
    call_args = mock_exec.call_args[0]
    assert "--output" in call_args
    assert "json" in call_args


# ---------------------------------------------------------------------------
# _raise_helpful_error
# ---------------------------------------------------------------------------

def test_raise_helpful_error_az_login_prompt():
    """Detects 'please run az login' pattern."""
    with pytest.raises(ado_client.ADOClientError, match="az login"):
        ado_client._raise_helpful_error("Please run 'az login' to authenticate", 1)


def test_raise_helpful_error_azure_connection_error():
    """Detects AzureConnectionError in stderr."""
    with pytest.raises(ado_client.ADOClientError, match="az login"):
        ado_client._raise_helpful_error("AzureConnectionError: no connection", 1)


def test_raise_helpful_error_missing_extension_explicit():
    """Detects explicit 'requires the extension azure-devops' message."""
    with pytest.raises(ado_client.ADOClientError, match="extension"):
        ado_client._raise_helpful_error(
            "The command requires the extension 'azure-devops'", 1
        )


def test_raise_helpful_error_az_repos_not_recognized():
    """Detects 'az repos' is not recognized."""
    with pytest.raises(ado_client.ADOClientError, match="extension"):
        ado_client._raise_helpful_error("'az repos' is not recognized as a command", 1)


def test_raise_helpful_error_az_boards_not_recognized():
    """Detects 'az boards' is not recognized."""
    with pytest.raises(ado_client.ADOClientError, match="extension"):
        ado_client._raise_helpful_error("'az boards' is not recognized as a command", 1)


def test_raise_helpful_error_generic_includes_exit_code():
    """Generic error includes the exit code in the message."""
    with pytest.raises(ado_client.ADOClientError, match="exited with code 2"):
        ado_client._raise_helpful_error("Unknown problem", 2)


def test_raise_helpful_error_truncates_long_stderr():
    """Generic error message handles stderr longer than 1000 chars."""
    long_stderr = "x" * 2000
    with pytest.raises(ado_client.ADOClientError) as exc_info:
        ado_client._raise_helpful_error(long_stderr, 3)
    assert len(str(exc_info.value)) < 1200  # well under 2000


# ---------------------------------------------------------------------------
# _fetch_prs_for_project
# ---------------------------------------------------------------------------

def test_fetch_prs_for_project_returns_list(monkeypatch):
    """_fetch_prs_for_project returns a list of raw dicts."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=json.dumps([_MINIMAL_PR]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        result = asyncio.run(ado_client._fetch_prs_for_project("Proj1", []))
    assert len(result) == 1
    assert result[0]["pullRequestId"] == 42


def test_fetch_prs_for_project_non_list_returns_empty(monkeypatch):
    """_fetch_prs_for_project returns [] when az returns a non-list."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=json.dumps({"error": "some error"}).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        result = asyncio.run(ado_client._fetch_prs_for_project("Proj1", []))
    assert result == []


# ---------------------------------------------------------------------------
# fetch_my_prs
# ---------------------------------------------------------------------------

def test_fetch_my_prs_happy_path(monkeypatch):
    """fetch_my_prs returns parsed PullRequest objects from all projects."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1"])
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=json.dumps([_MINIMAL_PR]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        prs = asyncio.run(ado_client.fetch_my_prs())
    assert len(prs) == 1
    assert prs[0].id == 42
    assert prs[0].title == "Test PR"


def test_fetch_my_prs_empty_response(monkeypatch):
    """fetch_my_prs returns empty list when az returns no results."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1"])
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=b"[]")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        prs = asyncio.run(ado_client.fetch_my_prs())
    assert prs == []


def test_fetch_my_prs_aggregates_multiple_projects(monkeypatch):
    """fetch_my_prs aggregates results from all configured projects."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1", "Proj2"])
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")

    pr1 = {**_MINIMAL_PR, "pullRequestId": 10}
    pr2 = {**_MINIMAL_PR, "pullRequestId": 20}
    call_count = 0

    async def fake_exec(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        p = make_proc(stdout=json.dumps([pr1]).encode()) if call_count == 1 \
            else make_proc(stdout=json.dumps([pr2]).encode())
        return p

    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=fake_exec):
        prs = asyncio.run(ado_client.fetch_my_prs())
    assert len(prs) == 2
    assert {p.id for p in prs} == {10, 20}


def test_fetch_my_prs_partial_pr_fields(monkeypatch):
    """fetch_my_prs tolerates PRs with only the required pullRequestId field."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1"])
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")

    sparse_pr = {
        "pullRequestId": 77,
        "createdBy": {},
        "repository": {"name": "Repo", "project": {"name": "Proj"}},
        "sourceRefName": "",
        "targetRefName": "",
        "creationDate": "",
    }
    proc = make_proc(stdout=json.dumps([sparse_pr]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        prs = asyncio.run(ado_client.fetch_my_prs())
    assert prs[0].id == 77
    assert prs[0].title == ""


# ---------------------------------------------------------------------------
# fetch_reviewing_prs
# ---------------------------------------------------------------------------

def test_fetch_reviewing_prs_happy_path(monkeypatch):
    """fetch_reviewing_prs returns PRs where current user is a reviewer."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1"])
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=json.dumps([_MINIMAL_PR]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        prs = asyncio.run(ado_client.fetch_reviewing_prs())
    assert len(prs) == 1


def test_fetch_reviewing_prs_with_reviewer_votes(monkeypatch):
    """fetch_reviewing_prs correctly parses reviewer vote data."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1"])
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")

    pr_with_votes = {
        **_MINIMAL_PR,
        "reviewers": [
            {"displayName": "Reviewer1", "uniqueName": "r1@example.com", "vote": 10, "hasDeclined": False},
            {"displayName": "Reviewer2", "uniqueName": "r2@example.com", "vote": -10, "hasDeclined": True},
        ],
    }
    proc = make_proc(stdout=json.dumps([pr_with_votes]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        prs = asyncio.run(ado_client.fetch_reviewing_prs())
    assert len(prs[0].reviewers) == 2
    assert prs[0].reviewers[0].vote == 10
    assert prs[0].reviewers[1].has_declined is True


def test_fetch_reviewing_prs_declined_reviewer_vote(monkeypatch):
    """fetch_reviewing_prs: declined reviewer (vote=-10, hasDeclined=True) is preserved."""
    monkeypatch.setattr(config, "PROJECTS", ["Proj1"])
    monkeypatch.setattr(config, "USER_EMAIL", "me@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")

    pr_data = {
        **_MINIMAL_PR,
        "reviewers": [
            {"displayName": "Me", "uniqueName": "me@example.com", "vote": -10, "hasDeclined": True},
        ],
    }
    proc = make_proc(stdout=json.dumps([pr_data]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        prs = asyncio.run(ado_client.fetch_reviewing_prs())
    assert prs[0].my_vote("me@example.com") == -10
    assert prs[0].has_declined("me@example.com") is True


# ---------------------------------------------------------------------------
# fetch_pr_detail
# ---------------------------------------------------------------------------

def test_fetch_pr_detail_happy_path(monkeypatch):
    """fetch_pr_detail returns a single PullRequest for a given PR ID."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=json.dumps(_MINIMAL_PR).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        pr = asyncio.run(ado_client.fetch_pr_detail(42))
    assert pr.id == 42
    assert pr.repo_name == "TestRepo"


def test_fetch_pr_detail_invalid_response_type_raises(monkeypatch):
    """fetch_pr_detail raises ADOClientError when az returns a list instead of dict."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=b"[1, 2, 3]")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        with pytest.raises(ado_client.ADOClientError, match="Unexpected response"):
            asyncio.run(ado_client.fetch_pr_detail(42))


# ---------------------------------------------------------------------------
# fetch_work_items
# ---------------------------------------------------------------------------

def test_fetch_work_items_happy_path(monkeypatch):
    """fetch_work_items returns a list of WorkItem objects."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    proc = make_proc(stdout=json.dumps([_MINIMAL_WI]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client.fetch_work_items())
    assert len(items) == 1
    assert items[0].id == 99
    assert items[0].title == "Test Work Item"


def test_fetch_work_items_empty_response(monkeypatch):
    """fetch_work_items returns empty list when az returns no work items."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    proc = make_proc(stdout=b"[]")
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client.fetch_work_items())
    assert items == []


def test_fetch_work_items_wiql_error_response(monkeypatch):
    """fetch_work_items returns [] when ADO returns an error dict (WIQL failure)."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    # ADO may return a dict with an error message on WIQL failures
    error_response = {"message": "TF401232: The query could not be parsed."}
    proc = make_proc(stdout=json.dumps(error_response).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client.fetch_work_items())
    assert items == []


def test_fetch_work_items_with_tags(monkeypatch):
    """fetch_work_items correctly splits semicolon-separated tags."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")

    wi_with_tags = {
        "id": 55,
        "fields": {
            **_MINIMAL_WI["fields"],
            "System.Tags": "tag1; tag2; tag3",
        },
    }
    proc = make_proc(stdout=json.dumps([wi_with_tags]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client.fetch_work_items())
    assert items[0].tags == ["tag1", "tag2", "tag3"]


def test_fetch_work_items_with_parent_id(monkeypatch):
    """fetch_work_items correctly parses System.Parent as parent_id."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")

    wi_with_parent = {
        "id": 55,
        "fields": {
            **_MINIMAL_WI["fields"],
            "System.Parent": 100,
        },
    }
    proc = make_proc(stdout=json.dumps([wi_with_parent]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client.fetch_work_items())
    assert items[0].parent_id == 100


# ---------------------------------------------------------------------------
# _fetch_work_items_by_ids
# ---------------------------------------------------------------------------

def test_fetch_work_items_by_ids_empty_returns_immediately():
    """_fetch_work_items_by_ids returns [] without calling az for empty list."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        result = asyncio.run(ado_client._fetch_work_items_by_ids([]))
    assert result == []
    mock_exec.assert_not_called()


def test_fetch_work_items_by_ids_happy_path(monkeypatch):
    """_fetch_work_items_by_ids returns WorkItems for the given IDs."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    proc = make_proc(stdout=json.dumps([_MINIMAL_WI]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client._fetch_work_items_by_ids([99]))
    assert len(items) == 1
    assert items[0].id == 99


def test_fetch_work_items_by_ids_non_list_returns_empty(monkeypatch):
    """_fetch_work_items_by_ids returns [] when az returns a non-list response."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    proc = make_proc(stdout=json.dumps({"error": "fail"}).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client._fetch_work_items_by_ids([1, 2]))
    assert items == []


# ---------------------------------------------------------------------------
# fetch_work_item_detail
# ---------------------------------------------------------------------------

def test_fetch_work_item_detail_happy_path(monkeypatch):
    """fetch_work_item_detail returns a WorkItem for the given ID."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    proc = make_proc(stdout=json.dumps(_MINIMAL_WI).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        wi = asyncio.run(ado_client.fetch_work_item_detail(99))
    assert wi.id == 99
    assert wi.work_item_type == "Task"


def test_fetch_work_item_detail_invalid_response_type_raises(monkeypatch):
    """fetch_work_item_detail raises ADOClientError when az returns a list."""
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    proc = make_proc(stdout=b'[{"id": 1}]')
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        with pytest.raises(ado_client.ADOClientError, match="Unexpected response"):
            asyncio.run(ado_client.fetch_work_item_detail(99))


# ---------------------------------------------------------------------------
# fetch_work_items_with_hierarchy
# ---------------------------------------------------------------------------

def test_fetch_work_items_with_hierarchy_no_parents(monkeypatch):
    """Items with no parent_id are returned as-is without extra fetches."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")
    proc = make_proc(stdout=json.dumps([_MINIMAL_WI]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        items = asyncio.run(ado_client.fetch_work_items_with_hierarchy())
    assert len(items) == 1
    assert items[0].is_context_parent is False


def test_fetch_work_items_with_hierarchy_fetches_missing_parent(monkeypatch):
    """fetch_work_items_with_hierarchy fetches parent items not owned by the user."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")

    child_wi = {
        "id": 99,
        "fields": {
            "System.Title": "Child Item",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.IterationPath": "",
            "System.AreaPath": "",
            "System.Tags": "",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
            "System.Parent": 100,
        },
    }
    parent_wi = {
        "id": 100,
        "fields": {
            "System.Title": "Parent User Story",
            "System.State": "Active",
            "System.WorkItemType": "User Story",
            "System.IterationPath": "",
            "System.AreaPath": "",
            "System.Tags": "",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
        },
    }

    call_count = 0

    async def fake_exec(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return make_proc(stdout=json.dumps([child_wi]).encode()) if call_count == 1 \
            else make_proc(stdout=json.dumps([parent_wi]).encode())

    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=fake_exec):
        items = asyncio.run(ado_client.fetch_work_items_with_hierarchy())

    assert len(items) == 2
    context_parents = [i for i in items if i.is_context_parent]
    assert len(context_parents) == 1
    assert context_parents[0].id == 100


def test_fetch_work_items_with_hierarchy_skips_known_parents(monkeypatch):
    """fetch_work_items_with_hierarchy does not re-fetch parents already in the list."""
    monkeypatch.setattr(config, "USER_EMAIL", "user@example.com")
    monkeypatch.setattr(config, "ORG_URL", "https://dev.azure.com/org")
    monkeypatch.setattr(config, "PROJECT", "TestProject")

    # Child points to parent that IS in the result set
    child_wi = {
        "id": 99,
        "fields": {
            "System.Title": "Child",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.IterationPath": "",
            "System.AreaPath": "",
            "System.Tags": "",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
            "System.Parent": 100,
        },
    }
    parent_wi = {
        "id": 100,
        "fields": {
            "System.Title": "Parent (also assigned to user)",
            "System.State": "Active",
            "System.WorkItemType": "User Story",
            "System.IterationPath": "",
            "System.AreaPath": "",
            "System.Tags": "",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
        },
    }

    # Both items returned in single initial fetch
    proc = make_proc(stdout=json.dumps([child_wi, parent_wi]).encode())
    with patch("shutil.which", return_value="/usr/bin/az"), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)) as mock_exec:
        items = asyncio.run(ado_client.fetch_work_items_with_hierarchy())

    assert len(items) == 2
    # Only one call — no secondary fetch needed
    assert mock_exec.call_count == 1
    assert all(not i.is_context_parent for i in items)
