"""Fictional fixture data for demo mode.

All data uses the clearly-invented ``middle-earth`` organization so it cannot
be mistaken for real Microsoft / Azure DevOps content.

Theme: Tolkien's Lord of the Rings — Thorin's Company cast (plus Fellowship).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ado_dashboard.models import (
    CopilotSession,
    PullRequest,
    Reviewer,
    TriageItem,
    WorkItem,
)

# ---------------------------------------------------------------------------
# Demo org / project constants
# ---------------------------------------------------------------------------
DEMO_ORG_URL = "https://dev.azure.com/middle-earth"
DEMO_PROJECT = "expedition"
DEMO_USER_EMAIL = "g.grey@middle-earth.example"

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
_NOW = datetime.now(tz=UTC)


def _ago(**kwargs: int) -> datetime:
    return _NOW - timedelta(**kwargs)


# ---------------------------------------------------------------------------
# Pull Requests — "Mine" (created by Gandalf / the demo user)
# ---------------------------------------------------------------------------
_MY_PRS_RAW: list[dict] = [
    {
        "pullRequestId": 1011,
        "title": "feat: implement One Ring bearer authentication flow",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL},
        "repository": {"name": "rings-of-power", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/feature/ring-bearer-auth",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(days=3).isoformat(),
        "reviewers": [
            {"displayName": "Aragorn Elessar", "uniqueName": "a.elessar@middle-earth.example", "vote": 10, "hasDeclined": False},
            {"displayName": "Legolas Greenleaf", "uniqueName": "l.greenleaf@middle-earth.example", "vote": 5, "hasDeclined": False},
        ],
        "labels": [{"name": "security"}, {"name": "auth"}],
        "description": "Implements the One Ring bearer auth flow with Mordor SSO integration.",
    },
    {
        "pullRequestId": 1012,
        "title": "fix: Orthanc smoke-signal parsing regression",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL},
        "repository": {"name": "moria-systems", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/fix/orthanc-smoke-signal",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(days=1, hours=4).isoformat(),
        "reviewers": [
            {"displayName": "Saruman the White", "uniqueName": "s.white@middle-earth.example", "vote": -10, "hasDeclined": False},
            {"displayName": "Radagast", "uniqueName": "r.brown@middle-earth.example", "vote": 0, "hasDeclined": False},
        ],
        "labels": [{"name": "bug"}, {"name": "regression"}],
        "description": "Fixes a regression in smoke-signal parsing introduced in v2.4.1.",
    },
    {
        "pullRequestId": 1013,
        "title": "docs: update Moria passage cartography API reference",
        "status": "active",
        "isDraft": True,
        "createdBy": {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL},
        "repository": {"name": "fellowship", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/docs/moria-cartography",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(hours=6).isoformat(),
        "reviewers": [],
        "labels": [{"name": "documentation"}],
        "description": "Draft: documenting the new cartography API endpoints.",
    },
    {
        "pullRequestId": 1014,
        "title": "refactor: consolidate hobbit resilience traits into base class",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL},
        "repository": {"name": "fellowship", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/refactor/hobbit-traits",
        "targetRefName": "refs/heads/develop",
        "creationDate": _ago(days=7).isoformat(),
        "reviewers": [
            {"displayName": "Frodo Baggins", "uniqueName": "f.baggins@middle-earth.example", "vote": 5, "hasDeclined": False},
            {"displayName": "Samwise Gamgee", "uniqueName": "s.gamgee@middle-earth.example", "vote": 10, "hasDeclined": False},
            {"displayName": "Merry Brandybuck", "uniqueName": "m.brandybuck@middle-earth.example", "vote": 0, "hasDeclined": False},
        ],
        "labels": [{"name": "refactor"}, {"name": "tech-debt"}],
        "description": "Moves shared resilience logic into HobbitBase to reduce duplication.",
    },
]

# ---------------------------------------------------------------------------
# Pull Requests — "Reviewing" (Gandalf is a reviewer)
# ---------------------------------------------------------------------------
_REVIEWING_PRS_RAW: list[dict] = [
    {
        "pullRequestId": 1021,
        "title": "feat: add Ent mobilization scheduling service",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Treebeard Fangorn", "uniqueName": "t.fangorn@middle-earth.example"},
        "repository": {"name": "rohan-ops", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/feature/ent-mobilization",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(days=5).isoformat(),
        "reviewers": [
            {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL, "vote": -5, "hasDeclined": False},
            {"displayName": "Théoden King", "uniqueName": "t.king@middle-earth.example", "vote": 0, "hasDeclined": False},
        ],
        "labels": [{"name": "feature"}, {"name": "orchestration"}],
        "description": "Adds background scheduler for Ent mobilization with Fangorn webhook support.",
    },
    {
        "pullRequestId": 1022,
        "title": "fix: resolve Mordor DNS lookup timeout under high orc load",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Frodo Baggins", "uniqueName": "f.baggins@middle-earth.example"},
        "repository": {"name": "moria-systems", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/fix/mordor-dns-timeout",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(days=2).isoformat(),
        "reviewers": [
            {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL, "vote": 10, "hasDeclined": False},
            {"displayName": "Samwise Gamgee", "uniqueName": "s.gamgee@middle-earth.example", "vote": 10, "hasDeclined": False},
        ],
        "labels": [{"name": "bug"}, {"name": "performance"}],
        "description": "Increases DNS retry budget and adds circuit-breaker for Mordor nameservers.",
    },
    {
        "pullRequestId": 1023,
        "title": "feat: multi-realm federated identity for Rivendell portal",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Legolas Greenleaf", "uniqueName": "l.greenleaf@middle-earth.example"},
        "repository": {"name": "rings-of-power", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/feature/rivendell-federation",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(days=4).isoformat(),
        "reviewers": [
            {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL, "vote": 0, "hasDeclined": False},
            {"displayName": "Elrond Half-elven", "uniqueName": "e.halfelven@middle-earth.example", "vote": 5, "hasDeclined": False},
            {"displayName": "Galadriel", "uniqueName": "g.lothlórien@middle-earth.example", "vote": 10, "hasDeclined": False},
        ],
        "labels": [{"name": "feature"}, {"name": "identity"}],
        "description": "Implements OIDC federation across Rivendell, Lothlórien, and Mirkwood realms.",
    },
    {
        "pullRequestId": 1024,
        "title": "chore: upgrade orc detection ML models to v3.2",
        "status": "active",
        "isDraft": True,
        "createdBy": {"displayName": "Gimli son of Glóin", "uniqueName": "g.gloin@middle-earth.example"},
        "repository": {"name": "moria-systems", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/chore/orc-detection-v3",
        "targetRefName": "refs/heads/feature/moria-defence",
        "creationDate": _ago(days=1).isoformat(),
        "reviewers": [
            {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL, "vote": 0, "hasDeclined": False},
            {"displayName": "Balin son of Fundin", "uniqueName": "b.fundin@middle-earth.example", "vote": 5, "hasDeclined": False},
        ],
        "labels": [{"name": "chore"}, {"name": "ml"}],
        "description": "Draft: bumping orc detection models; running internal benchmarks.",
    },
    {
        "pullRequestId": 1025,
        "title": "fix: Balrog collision detection causes critical service crash",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Boromir of Gondor", "uniqueName": "b.gondor@middle-earth.example"},
        "repository": {"name": "moria-systems", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/fix/balrog-collision",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(hours=18).isoformat(),
        "reviewers": [
            {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL, "vote": -10, "hasDeclined": False},
            {"displayName": "Aragorn Elessar", "uniqueName": "a.elessar@middle-earth.example", "vote": -5, "hasDeclined": False},
        ],
        "labels": [{"name": "critical"}, {"name": "bug"}],
        "description": "The fix addresses a stack overflow in Balrog physics engine.",
    },
    {
        "pullRequestId": 1026,
        "title": "feat: implement stealth mode for ring-bearer service mesh",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Aragorn Elessar", "uniqueName": "a.elessar@middle-earth.example"},
        "repository": {"name": "rings-of-power", "project": {"name": DEMO_PROJECT}},
        "sourceRefName": "refs/heads/feature/stealth-mode",
        "targetRefName": "refs/heads/main",
        "creationDate": _ago(days=6).isoformat(),
        "reviewers": [
            {"displayName": "Gandalf the Grey", "uniqueName": DEMO_USER_EMAIL, "vote": 10, "hasDeclined": False},
            {"displayName": "Arwen Undómiel", "uniqueName": "a.undomiel@middle-earth.example", "vote": 10, "hasDeclined": False},
        ],
        "labels": [{"name": "feature"}, {"name": "security"}],
        "description": "Adds Sauron-evading stealth routing for ring-bearer service mesh traffic.",
    },
]


def _make_prs(raw: list[dict], org_url: str = DEMO_ORG_URL) -> list[PullRequest]:
    """Build PullRequest objects directly from fixture dicts."""
    prs: list[PullRequest] = []
    for d in raw:
        reviewers = [
            Reviewer(
                name=r["displayName"],
                vote=r.get("vote", 0),
                email=r.get("uniqueName", ""),
                has_declined=r.get("hasDeclined", False),
            )
            for r in d.get("reviewers", [])
        ]
        labels = [lb["name"] for lb in d.get("labels", [])]
        repo = d["repository"]
        proj = repo["project"]["name"]
        pr_id = d["pullRequestId"]
        created_by = d.get("createdBy", {})
        author = created_by.get("displayName", "Unknown")
        prs.append(PullRequest(
            id=pr_id,
            title=d["title"],
            status=d.get("status", "active"),
            is_draft=d.get("isDraft", False),
            author=author,
            repo_name=repo["name"],
            project=proj,
            source_branch=d["sourceRefName"],
            target_branch=d["targetRefName"],
            created_date=_parse_demo_date(d["creationDate"]),
            reviewers=reviewers,
            labels=labels,
            url=f"{org_url}/{proj}/_git/{repo['name']}/pullrequest/{pr_id}",
            description=d.get("description"),
        ))
    return prs


def _parse_demo_date(raw: str) -> datetime:
    """Parse an ISO-8601 string that may include fractional seconds."""
    try:
        if raw.endswith("+00:00") or raw.endswith("Z"):
            return datetime.fromisoformat(raw.rstrip("Z") + "+00:00")
        return datetime.fromisoformat(raw)
    except ValueError:
        return _NOW


# ---------------------------------------------------------------------------
# Work Items — hierarchy: Epics → Features → Stories/Tasks/Bugs
# ---------------------------------------------------------------------------
def _wi(
    wi_id: int,
    title: str,
    wi_type: str,
    state: str,
    iteration: str = "expedition\\Sprint 7",
    area: str = "expedition\\Core",
    tags: list[str] | None = None,
    priority: int | None = None,
    parent_id: int | None = None,
    is_context_parent: bool = False,
    changed_days_ago: int = 1,
    description: str = "",
) -> WorkItem:
    return WorkItem(
        id=wi_id,
        title=title,
        state=state,
        work_item_type=wi_type,
        iteration_path=iteration,
        area_path=area,
        tags=tags or [],
        changed_date=_ago(days=changed_days_ago),
        url=f"{DEMO_ORG_URL}/{DEMO_PROJECT}/_workitems/edit/{wi_id}",
        description=description,
        priority=priority,
        parent_id=parent_id,
        is_context_parent=is_context_parent,
    )


DEMO_WORK_ITEMS: list[WorkItem] = [
    # --- Epics (context parents, not assigned to demo user) ---
    _wi(10010, "Epic: Fellowship Mission Planning", "Epic", "Active",
        is_context_parent=True, changed_days_ago=14, priority=1),
    _wi(10020, "Epic: Mordor Infrastructure Hardening", "Epic", "Active",
        is_context_parent=True, changed_days_ago=7, priority=1),

    # --- Features (context parents) ---
    _wi(20010, "Ring Disposal Protocol", "Feature", "Active",
        parent_id=10010, is_context_parent=True, changed_days_ago=5, priority=1),
    _wi(20020, "Palantír Monitoring Network", "Feature", "Active",
        parent_id=10020, is_context_parent=True, changed_days_ago=3, priority=2),

    # --- User Stories assigned to demo user ---
    _wi(30010, "Implement hobbit route-planning algorithm for Mount Doom approach",
        "User Story", "Active", parent_id=20010, priority=1, changed_days_ago=2,
        description="Route planner must avoid Mordor checkpoints and nazgûl patrol paths."),
    _wi(30020, "Design Rivendell API gateway with elvish rate-limiting",
        "User Story", "New", parent_id=20010, priority=2, changed_days_ago=4,
        description="Rate-limiting based on perceived threat level from Sauron."),
    _wi(30030, "Build Mordor firewall bypass for Grey Havens traffic",
        "User Story", "Active", parent_id=20020, priority=1, changed_days_ago=1,
        description="Bypass must route through Rohan relay nodes."),
    _wi(30040, "Document fellowship authentication ceremony",
        "User Story", "Resolved", parent_id=20010, priority=3, changed_days_ago=6,
        description="Document the nine walkers oath-signing process for on-boarding."),

    # --- Tasks ---
    _wi(40010, "Write unit tests for lembas-based session persistence",
        "Task", "Active", parent_id=30010, priority=2, changed_days_ago=1,
        tags=["testing", "session"]),
    _wi(40020, "Deploy miruvor healing service to staging cluster",
        "Task", "Resolved", parent_id=30010, priority=2, changed_days_ago=3,
        tags=["deploy", "infra"]),
    _wi(40030, "Configure Eagle transport endpoint health checks",
        "Task", "New", parent_id=30020, priority=3, changed_days_ago=2,
        tags=["infra", "health-check"]),

    # --- Bugs ---
    _wi(50010, "Shadow visibility detection fails at Weathertop under fog",
        "Bug", "Active", priority=1, changed_days_ago=0,
        tags=["critical", "visibility"],
        description="Detection service returns false negative when fog density exceeds 80%."),
    _wi(50020, "Palantír session timeout too short for long-distance scrying",
        "Bug", "New", priority=2, changed_days_ago=2,
        tags=["ux", "timeout"],
        description="30-second timeout insufficient for Barad-dûr comms. Recommend 300s."),
    _wi(50030, "Gondor beacon signal corrupted by Mordor interference",
        "Bug", "Active", priority=2, changed_days_ago=1,
        tags=["signal", "corruption"],
        description="Beacon acknowledgement packets corrupted 15% of the time."),
    _wi(50040, "Ent movement-speed calculation overflows on >3000-year age",
        "Bug", "Resolved", priority=3, changed_days_ago=5,
        tags=["math", "overflow"],
        description="Integer overflow at epoch > 3000 years. Fixed with uint64 cast."),
]


# ---------------------------------------------------------------------------
# Triage Items
# ---------------------------------------------------------------------------
DEMO_TRIAGE_ITEMS: list[TriageItem] = [
    TriageItem(
        id=60010,
        title="[Expedition Board] - Balrog containment service crashes on cold start",
        description="The Balrog containment microservice panics on startup if shadow-bridge config is missing.",
        created_date="2026-07-14",
        age_days=3,
        assigned_to="b.gondor@middle-earth.example",
        pr_id=1025,
        tags="critical; crash",
        priority=1,
        work_item_type="Bug",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Blocking Issue",
        urgency_rank=1,
        ai_why="Balrog containment crash blocks all Moria deployments · PR #1025",
    ),
    TriageItem(
        id=60020,
        title="[Expedition Board] - Mordor DNS resolver not respecting TTL",
        description="DNS TTL values from Mordor nameservers are ignored; cache never refreshes.",
        created_date="2026-07-12",
        age_days=5,
        assigned_to="f.baggins@middle-earth.example",
        pr_id=None,
        tags="dns; networking",
        priority=1,
        work_item_type="Bug",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Bug / Behavior",
        urgency_rank=2,
        ai_why="DNS cache never expires — stale Mordor IPs cause 502 errors",
    ),
    TriageItem(
        id=60030,
        title="[Expedition Board] - PR review: Ring encryption key rotation",
        description="Please review the key rotation strategy for Ring bearer encryption tokens.",
        created_date="2026-07-15",
        age_days=2,
        assigned_to="g.grey@middle-earth.example",
        pr_id=1011,
        tags="security; review",
        priority=2,
        work_item_type="Task",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="PR Review",
        urgency_rank=3,
        ai_why="Security review for ring encryption · PR #1011",
    ),
    TriageItem(
        id=60040,
        title="[Expedition Board] - Add Ent webhook support for deforestation alerts",
        description="Fangorn forest requires webhook notifications when logging operations approach borders.",
        created_date="2026-07-10",
        age_days=7,
        assigned_to="t.fangorn@middle-earth.example",
        pr_id=None,
        tags="feature; webhook",
        priority=2,
        work_item_type="User Story",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Feature Request",
        urgency_rank=4,
        ai_why="Ent mobilization depends on deforestation webhook",
    ),
    TriageItem(
        id=60050,
        title="[Expedition Board] - How do I configure multi-realm Palantír access?",
        description="User asks how to configure the Palantír to show feeds from multiple realms simultaneously.",
        created_date="2026-07-14",
        age_days=3,
        assigned_to="Unassigned",
        pr_id=None,
        tags="question; config",
        priority=3,
        work_item_type="Task",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Support Question",
        urgency_rank=5,
        ai_why="Config question about multi-realm Palantír — needs docs link",
    ),
    TriageItem(
        id=60060,
        title="[Expedition Board] - Nazgûl probe timeout too aggressive",
        description="The nazgûl detection probe times out in 500ms; should be at least 2000ms for Weathertop.",
        created_date="2026-07-11",
        age_days=6,
        assigned_to="a.elessar@middle-earth.example",
        pr_id=None,
        tags="bug; timeout",
        priority=2,
        work_item_type="Bug",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Bug / Behavior",
        urgency_rank=2,
        ai_why="500ms timeout causes false-positive nazgûl alerts",
    ),
    TriageItem(
        id=60070,
        title="[Expedition Board] - Deploy Rohan cavalry dispatch service to prod",
        description="The cavalry dispatch service is ready; waiting on Théoden approval to deploy to production.",
        created_date="2026-07-13",
        age_days=4,
        assigned_to="t.king@middle-earth.example",
        pr_id=None,
        tags="deploy; production",
        priority=1,
        work_item_type="Task",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Blocking Issue",
        urgency_rank=1,
        ai_why="Prod deployment blocked on king approval — cavalry offline",
    ),
    TriageItem(
        id=60080,
        title="[Expedition Board] - Request: add CSV export for triage board",
        description="Team requests CSV export capability for sprint review reports.",
        created_date="2026-07-08",
        age_days=9,
        assigned_to="Unassigned",
        pr_id=None,
        tags="feature; export",
        priority=3,
        work_item_type="User Story",
        board="https://dev.azure.com/middle-earth/expedition/_boards/board/t/Fellowship/Triage",
        category="Feature Request",
        urgency_rank=4,
        ai_why="CSV export requested for sprint review reporting",
    ),
]


# ---------------------------------------------------------------------------
# Copilot Sessions
# ---------------------------------------------------------------------------
DEMO_SESSIONS: list[CopilotSession] = [
    CopilotSession(
        id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        summary="Implementing Ring bearer authentication flow",
        cwd="C:/repos/middle-earth/rings-of-power",
        git_root="C:/repos/middle-earth/rings-of-power",
        branch="feature/ring-bearer-auth",
        created_at=_ago(hours=2),
        updated_at=_ago(minutes=5),
        is_active=True,
        pid=12345,
        intent="Writing unit tests for bearer token validation",
        event_count=87,
        copilot_version="1.4.2",
    ),
    CopilotSession(
        id="b2c3d4e5-f6a7-8901-bcde-f12345678901",
        summary="Debugging Mordor DNS timeout regression",
        cwd="C:/repos/middle-earth/moria-systems",
        git_root="C:/repos/middle-earth/moria-systems",
        branch="fix/mordor-dns-timeout",
        created_at=_ago(hours=5),
        updated_at=_ago(minutes=45),
        is_active=True,
        pid=23456,
        intent="Fixing DNS retry logic with circuit breaker",
        event_count=134,
        copilot_version="1.4.2",
    ),
    CopilotSession(
        id="c3d4e5f6-a7b8-9012-cdef-123456789012",
        summary="Rohan cavalry dispatch service deployment",
        cwd="C:/repos/middle-earth/rohan-ops",
        git_root="C:/repos/middle-earth/rohan-ops",
        branch="main",
        created_at=_ago(days=1, hours=3),
        updated_at=_ago(hours=10),
        is_active=False,
        pid=None,
        intent="Reviewing Helm chart values for prod deploy",
        event_count=52,
        copilot_version="1.4.1",
    ),
    CopilotSession(
        id="d4e5f6a7-b8c9-0123-defa-234567890123",
        summary="Orc detection ML model upgrade",
        cwd="C:/repos/middle-earth/moria-systems",
        git_root="C:/repos/middle-earth/moria-systems",
        branch="chore/orc-detection-v3",
        created_at=_ago(days=2),
        updated_at=_ago(days=1, hours=6),
        is_active=False,
        pid=None,
        intent="Benchmarking v3.2 detection accuracy on Moria dataset",
        event_count=203,
        copilot_version="1.4.1",
    ),
    CopilotSession(
        id="e5f6a7b8-c9d0-1234-efab-345678901234",
        summary="Fellowship API gateway documentation",
        cwd="C:/repos/middle-earth/fellowship",
        git_root="C:/repos/middle-earth/fellowship",
        branch="docs/moria-cartography",
        created_at=_ago(days=4),
        updated_at=_ago(days=3, hours=2),
        is_active=False,
        pid=None,
        intent="Writing OpenAPI spec for cartography endpoints",
        event_count=31,
        copilot_version="1.4.0",
    ),
]


# ---------------------------------------------------------------------------
# Pre-built fixture lists (call once at startup — no side effects)
# ---------------------------------------------------------------------------
def get_my_prs() -> list[PullRequest]:
    """Return demo 'My PRs' fixture list."""
    return _make_prs(_MY_PRS_RAW)


def get_reviewing_prs() -> list[PullRequest]:
    """Return demo 'Reviewing' PRs fixture list."""
    return _make_prs(_REVIEWING_PRS_RAW)


def get_work_items() -> list[WorkItem]:
    """Return demo work items fixture list."""
    return list(DEMO_WORK_ITEMS)


def get_triage_items() -> list[TriageItem]:
    """Return demo triage items fixture list."""
    return list(DEMO_TRIAGE_ITEMS)


def get_sessions() -> list[CopilotSession]:
    """Return demo Copilot sessions fixture list."""
    return list(DEMO_SESSIONS)
