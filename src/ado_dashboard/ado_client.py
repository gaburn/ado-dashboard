"""Async Azure DevOps client that shells out to the ``az`` CLI."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from typing import Any

from ado_dashboard import config
from ado_dashboard.models import PullRequest, WorkItem

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ADOClientError(Exception):
    """Raised when an ``az`` CLI command fails."""


class ConcurrencyError(ADOClientError):
    """Raised when a work item was modified between read and write.

    The caller's ``rev`` no longer matches the server's current revision.
    The UI is expected to offer a refresh/merge/overwrite resolution.
    """


class ValidationError(ADOClientError):
    """Raised when ADO rejects a field update as invalid (HTTP 400 class).

    Examples: required field missing, value not in the allowed picklist,
    state transition not permitted by the work-item type's workflow.
    """


class PermissionError(ADOClientError):  # noqa: A001 - intentional shadow within module
    """Raised when the caller lacks write access (HTTP 401/403 class).

    Named to match Python's builtin for consumer convenience; the
    ``ADOClientError`` base disambiguates when both are imported.
    """


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


# ---------------------------------------------------------------------------
# Work-item writes (Issue #3, track #3-a)
# ---------------------------------------------------------------------------
# Field-name allow-list for v1. Keeps callers from passing arbitrary System.*
# fields (e.g. System.WorkItemType — that requires a different endpoint and is
# explicitly deferred to issue #4).
_EDITABLE_FIELDS: frozenset[str] = frozenset({
    "System.Title",
    "System.State",
    "System.IterationPath",
    "System.AreaPath",
    "System.Description",
})


def _classify_write_error(stderr: str, returncode: int | None) -> ADOClientError:
    """Translate ``az boards work-item update`` failures into typed errors."""
    lower = stderr.lower()

    # Auth/permission — ADO returns TF401019/TF401027 plus generic "forbidden".
    if (
        "tf401019" in lower
        or "tf401027" in lower
        or "vs403220" in lower
        or "forbidden" in lower
        or "not authorized" in lower
        or "do not have permission" in lower
        or "does not have permission" in lower
        or "unauthorized" in lower
    ):
        return PermissionError(
            "You do not have permission to update this work item.\n"
            f"az stderr: {stderr[:500]}"
        )

    # Concurrency — rev mismatch is normally caught client-side, but the server
    # may still reject if someone updates between our refetch and write.
    if (
        "vs402625" in lower
        or "vs403357" in lower
        or "has been updated by another" in lower
        or "outdated revision" in lower
        or "is not the latest revision" in lower
        or ("rev " in lower and "mismatch" in lower)
    ):
        return ConcurrencyError(
            "Work item was modified by another user between read and write. "
            "Refresh and try again.\n"
            f"az stderr: {stderr[:500]}"
        )

    # Validation — invalid field value, disallowed transition, required field
    # missing. ADO uses TF237124, TF401320, "validation", "invalid value".
    if (
        "tf237124" in lower
        or "tf401320" in lower
        or "validation" in lower
        or "invalid value" in lower
        or "is not a valid" in lower
        or "is required" in lower
        or "transition" in lower and "not allowed" in lower
    ):
        return ValidationError(
            f"ADO rejected the update as invalid.\naz stderr: {stderr[:500]}"
        )

    # Fall through — generic failure.
    return ADOClientError(
        f"az work-item update failed with code {returncode}.\nstderr: {stderr[:1000]}"
    )


async def update_work_item(
    work_item_id: int,
    rev: int,
    field_updates: dict[str, Any],
) -> WorkItem:
    """Update editable fields on a work item with optimistic concurrency.

    The caller passes the ``rev`` they last observed. ADO itself enforces
    optimistic concurrency on writes — if another user updated the work item
    in the meantime, the ``az`` CLI surfaces an error (commonly ``VS403357``)
    which we translate into :class:`ConcurrencyError`. We do **not** do a
    pre-write refetch; that would double round-trips and still leaves a race
    window. The server is the source of truth.

    :param work_item_id: ADO work-item ID to update.
    :param rev: The ``rev`` value the caller last observed. Forwarded to ADO
        so the server can detect a stale-write race.
    :param field_updates: Mapping of ADO field name → new value. Keys must be
        in :data:`_EDITABLE_FIELDS` (Title, State, IterationPath, AreaPath,
        Description); other keys raise :class:`ValueError`. Type-change is
        explicitly out of scope for v1 — see issue #4.
    :raises ConcurrencyError: The work item was modified between read and
        write (caller's ``rev`` is stale).
    :raises ValidationError: ADO rejected a field value (HTTP 400 class).
    :raises PermissionError: Caller lacks write access (HTTP 401/403 class).
    :raises ADOClientError: Any other ``az`` CLI failure.
    :returns: A fresh :class:`WorkItem` reflecting the post-update state.
    """
    if not field_updates:
        raise ValueError("field_updates must contain at least one field")

    bad_fields = set(field_updates) - _EDITABLE_FIELDS
    if bad_fields:
        raise ValueError(
            f"Fields not editable in v1: {sorted(bad_fields)}. "
            f"Allowed: {sorted(_EDITABLE_FIELDS)}. "
            "Type-change is deferred to issue #4."
        )

    log.info(
        "Updating work item #%d (rev=%d) fields=%s",
        work_item_id, rev, sorted(field_updates),
    )

    # Build ``--fields k=v k2=v2`` tokens. ``az`` parses each as one string;
    # newlines (Description) pass through unchanged.
    field_args = [f"{key}={value}" for key, value in field_updates.items()]

    args = [
        "boards", "work-item", "update",
        "--id", str(work_item_id),
        "--org", config.ORG_URL,
        "--fields", *field_args,
    ]

    try:
        data = await _run_az(args)
    except ADOClientError as exc:
        # _run_az prettified a few generic stderr patterns; for the write path
        # we re-classify into the typed conflict/validation/permission tree.
        raise _classify_write_error(str(exc), None) from exc

    if not isinstance(data, dict):
        raise ADOClientError(
            f"Unexpected response type for work item update #{work_item_id}"
        )
    return WorkItem.from_az_json(data)


# ---------------------------------------------------------------------------
# Metadata lookups with in-process caching
# ---------------------------------------------------------------------------
# Caches live for the process lifetime. ``refresh_caches()`` clears all three
# (wired into Settings → "Refresh caches" by Thorin's screen track).
#
# Keys:
#   _ALLOWED_STATES_CACHE: (project, work_item_type) → list[str]
#   _ITERATIONS_CACHE: project → list[str]
#   _AREAS_CACHE: project → list[str]
_ALLOWED_STATES_CACHE: dict[tuple[str, str], list[str]] = {}
_ITERATIONS_CACHE: dict[str, list[str]] = {}
_AREAS_CACHE: dict[str, list[str]] = {}


def refresh_caches() -> None:
    """Clear all metadata caches. Call from Settings 'Refresh' affordance."""
    _ALLOWED_STATES_CACHE.clear()
    _ITERATIONS_CACHE.clear()
    _AREAS_CACHE.clear()


def _flatten_node_paths(node: dict, prefix: str = "") -> list[str]:
    """Walk an ADO classification-node tree, yielding full path strings.

    ADO returns iteration/area nodes as:
        {"name": "Project", "children": [{"name": "Sprint 1", ...}, ...]}

    The full path uses backslash separators to match the values ADO stores
    on ``System.IterationPath`` / ``System.AreaPath``.
    """
    name = node.get("name", "")
    path = f"{prefix}\\{name}" if prefix else name
    out: list[str] = [path]
    for child in node.get("children") or []:
        out.extend(_flatten_node_paths(child, path))
    return out


async def get_allowed_states(
    work_item_type: str,
    current_state: str = "",  # noqa: ARG001 - reserved for v2 transition filtering
    project: str | None = None,
) -> list[str]:
    """Return the list of states defined for a work-item type.

    v1 returns *all* states for the type — UI is expected to default the
    Select to ``current_state``. A future revision may filter to only the
    transitions ADO permits from ``current_state``.

    Cached per ``(project, work_item_type)`` for the process lifetime.
    """
    proj = project or config.PROJECT
    cache_key = (proj, work_item_type)
    cached = _ALLOWED_STATES_CACHE.get(cache_key)
    if cached is not None:
        return cached

    log.info("Fetching allowed states for type=%s project=%s", work_item_type, proj)
    # REST: GET /{project}/_apis/wit/workitemtypes/{type}/states?api-version=7.1-preview
    # Wrapped via ``az devops invoke`` so we stay on a single transport.
    # NOTE: the resource is ``workitemtypestates`` (singular trailing "s") and
    # the API version must be the ``-preview`` qualifier; using ``7.1`` plain
    # causes the CLI to reject with "--resource and --api-version combination
    # is not correct", and ``workitemtypesstates`` (plural-plural) is not a
    # valid resource name. We learned this the hard way on real work items.
    data = await _run_az([
        "devops", "invoke",
        "--area", "wit",
        "--resource", "workitemtypestates",
        "--route-parameters", f"project={proj}", f"type={work_item_type}",
        "--api-version", "7.1-preview",
        "--org", config.ORG_URL,
    ])

    values: list[dict] = []
    if isinstance(data, dict):
        values = data.get("value") or []
    elif isinstance(data, list):
        values = data

    states = [v.get("name", "") for v in values if isinstance(v, dict) and v.get("name")]
    _ALLOWED_STATES_CACHE[cache_key] = states
    return states


async def get_iterations(project: str | None = None) -> list[str]:
    """Return the flattened iteration paths available in ``project``.

    Cached per project for the process lifetime.
    """
    proj = project or config.PROJECT
    cached = _ITERATIONS_CACHE.get(proj)
    if cached is not None:
        return cached

    log.info("Fetching iteration tree for project=%s", proj)
    data = await _run_az([
        "boards", "iteration", "project", "list",
        "--project", proj,
        "--org", config.ORG_URL,
    ])

    iterations: list[str] = []
    if isinstance(data, dict):
        iterations = _flatten_node_paths(data)
    elif isinstance(data, list):
        for root in data:
            if isinstance(root, dict):
                iterations.extend(_flatten_node_paths(root))

    _ITERATIONS_CACHE[proj] = iterations
    return iterations


async def get_areas(project: str | None = None) -> list[str]:
    """Return the flattened area paths available in ``project``.

    Cached per project for the process lifetime.
    """
    proj = project or config.PROJECT
    cached = _AREAS_CACHE.get(proj)
    if cached is not None:
        return cached

    log.info("Fetching area tree for project=%s", proj)
    data = await _run_az([
        "boards", "area", "project", "list",
        "--project", proj,
        "--org", config.ORG_URL,
    ])

    areas: list[str] = []
    if isinstance(data, dict):
        areas = _flatten_node_paths(data)
    elif isinstance(data, list):
        for root in data:
            if isinstance(root, dict):
                areas.extend(_flatten_node_paths(root))

    _AREAS_CACHE[proj] = areas
    return areas
