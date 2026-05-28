"""Async Azure DevOps client that shells out to the ``az`` CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil

from ado_dashboard import config
from ado_dashboard.models import PullRequest, WorkItem

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ADOClientError(Exception):
    """Raised when an ``az`` CLI command fails."""


# ---------------------------------------------------------------------------
# Low-level runner
# ---------------------------------------------------------------------------
async def _run_az(args: list[str]) -> dict | list:
    """Run an ``az`` CLI command and return parsed JSON.

    Raises :class:`ADOClientError` with an actionable message on failure.
    """
    az_path = shutil.which("az")
    if az_path is None:
        raise ADOClientError(
            "Azure CLI ('az') not found on PATH. "
            "Install it from https://aka.ms/install-azure-cli and restart your shell."
        )

    cmd = [az_path, *args, "--output", "json"]
    log.debug("az command: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        _raise_helpful_error(stderr, proc.returncode)

    if not stdout:
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ADOClientError(
            f"Failed to parse az CLI JSON output: {exc}\nRaw output: {stdout[:500]}"
        ) from exc


def _raise_helpful_error(stderr: str, returncode: int | None) -> None:
    """Translate common ``az`` errors into human-friendly messages."""
    lower = stderr.lower()

    if "please run 'az login'" in lower or "azureconnectionerror" in lower:
        raise ADOClientError(
            "Not authenticated. Run `az login` first, then retry."
        )

    if "the command requires the extension 'azure-devops'" in lower:
        raise ADOClientError(
            "Azure DevOps CLI extension is missing. "
            "Run `az extension add --name azure-devops` to install it."
        )

    if "'az repos' is not recognized" in lower or "'az boards' is not recognized" in lower:
        raise ADOClientError(
            "Azure DevOps CLI extension is missing. "
            "Run `az extension add --name azure-devops` to install it."
        )

    raise ADOClientError(
        f"az CLI exited with code {returncode}.\nstderr: {stderr[:1000]}"
    )


# ---------------------------------------------------------------------------
# Pull Requests
# ---------------------------------------------------------------------------
async def _fetch_prs_for_project(project: str, extra_args: list[str]) -> list[dict]:
    """Fetch PRs from a single project with the given extra CLI args."""
    data = await _run_az([
        "repos", "pr", "list",
        *extra_args,
        "--status", "active",
        "--top", "50",
        "--org", config.ORG_URL,
        "--project", project,
    ])
    if not isinstance(data, list):
        return []
    return data


async def fetch_my_prs() -> list[PullRequest]:
    """Fetch PRs created by the current user across all configured projects."""
    log.info("Fetching PRs created by %s from projects %s", config.USER_EMAIL, config.PROJECTS)
    results = await asyncio.gather(*(
        _fetch_prs_for_project(project, ["--creator", config.USER_EMAIL])
        for project in config.PROJECTS
    ))
    return [PullRequest.from_az_json(pr) for batch in results for pr in batch]


async def fetch_reviewing_prs() -> list[PullRequest]:
    """Fetch PRs where the current user is a reviewer across all configured projects."""
    log.info("Fetching PRs where %s is a reviewer from projects %s", config.USER_EMAIL, config.PROJECTS)
    results = await asyncio.gather(*(
        _fetch_prs_for_project(project, ["--reviewer", config.USER_EMAIL])
        for project in config.PROJECTS
    ))
    return [PullRequest.from_az_json(pr) for batch in results for pr in batch]


async def fetch_pr_detail(pr_id: int) -> PullRequest:
    """Fetch full details for a single pull request."""
    log.info("Fetching PR detail for #%d", pr_id)
    data = await _run_az([
        "repos", "pr", "show",
        "--id", str(pr_id),
        "--org", config.ORG_URL,
    ])
    if not isinstance(data, dict):
        raise ADOClientError(f"Unexpected response type for PR #{pr_id}")
    return PullRequest.from_az_json(data)


# ---------------------------------------------------------------------------
# Work Items
# ---------------------------------------------------------------------------
_WORK_ITEMS_WIQL = (
    "SELECT [System.Id], [System.Title], [System.State], "
    "[System.WorkItemType], [System.IterationPath], [System.AreaPath], "
    "[System.Tags], [System.ChangedDate], [System.Description], "
    "[Microsoft.VSTS.Common.Priority], [System.Parent] "
    "FROM WorkItems "
    "WHERE [System.AssignedTo] = '{email}' "
    "AND [System.State] NOT IN ('Closed', 'Removed', 'Done', 'Completed', 'Cut', 'Resolved') "
    "ORDER BY [System.ChangedDate] DESC"
)

_WORK_ITEMS_BY_IDS_WIQL = (
    "SELECT [System.Id], [System.Title], [System.State], "
    "[System.WorkItemType], [System.IterationPath], [System.AreaPath], "
    "[System.Tags], [System.ChangedDate], [System.Description], "
    "[Microsoft.VSTS.Common.Priority], [System.Parent] "
    "FROM WorkItems "
    "WHERE [System.Id] IN ({ids})"
)


async def fetch_work_items() -> list[WorkItem]:
    """Fetch active work items assigned to the current user."""
    log.info("Fetching work items assigned to %s", config.USER_EMAIL)
    wiql = _WORK_ITEMS_WIQL.format(email=config.USER_EMAIL)
    data = await _run_az([
        "boards", "query",
        "--wiql", wiql,
        "--org", config.ORG_URL,
        "--project", config.PROJECT,
    ])
    if not isinstance(data, list):
        data = []
    return [WorkItem.from_az_json(wi) for wi in data]


async def _fetch_work_items_by_ids(ids: list[int]) -> list[WorkItem]:
    """Fetch work items by their IDs (for parent context)."""
    if not ids:
        return []
    id_list = ", ".join(str(i) for i in ids)
    wiql = _WORK_ITEMS_BY_IDS_WIQL.format(ids=id_list)
    data = await _run_az([
        "boards", "query",
        "--wiql", wiql,
        "--org", config.ORG_URL,
        "--project", config.PROJECT,
    ])
    if not isinstance(data, list):
        return []
    return [WorkItem.from_az_json(wi) for wi in data]


async def fetch_work_items_with_hierarchy() -> list[WorkItem]:
    """Fetch user's work items plus parent/grandparent items for hierarchy display.

    Parent items not assigned to the user are marked with ``is_context_parent=True``
    so the UI can display them as grouping headers rather than actionable items.
    """
    items = await fetch_work_items()
    known_ids = {wi.id for wi in items}

    # Fetch missing parents (one level up)
    missing_parent_ids = [
        wi.parent_id for wi in items
        if wi.parent_id and wi.parent_id not in known_ids
    ]
    if missing_parent_ids:
        parents = await _fetch_work_items_by_ids(list(set(missing_parent_ids)))
        for p in parents:
            p.is_context_parent = True
        items.extend(parents)
        known_ids.update(p.id for p in parents)

    # Fetch missing grandparents (one more level up)
    missing_gp_ids = [
        wi.parent_id for wi in items
        if wi.parent_id and wi.parent_id not in known_ids
    ]
    if missing_gp_ids:
        grandparents = await _fetch_work_items_by_ids(list(set(missing_gp_ids)))
        for gp in grandparents:
            gp.is_context_parent = True
        items.extend(grandparents)

    return items


async def fetch_work_item_detail(wi_id: int) -> WorkItem:
    """Fetch full details for a single work item."""
    log.info("Fetching work item detail for #%d", wi_id)
    data = await _run_az([
        "boards", "work-item", "show",
        "--id", str(wi_id),
        "--org", config.ORG_URL,
    ])
    if not isinstance(data, dict):
        raise ADOClientError(f"Unexpected response type for work item #{wi_id}")
    return WorkItem.from_az_json(data)
