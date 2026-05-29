"""Data models for Azure DevOps pull requests, work items, and triage items."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from ado_dashboard import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_ado_date(raw: str | None) -> datetime:
    """Parse an ADO ISO-8601 date string into a timezone-aware datetime."""
    if not raw:
        return datetime.now(tz=UTC)
    # ADO dates look like "2024-06-15T10:23:45.1234567Z" — Python needs at
    # most 6 fractional digits, so truncate.
    cleaned = raw.rstrip("Z")
    if "." in cleaned:
        base, frac = cleaned.split(".", 1)
        cleaned = f"{base}.{frac[:6]}"
    return datetime.fromisoformat(f"{cleaned}+00:00")


def _human_age(dt: datetime) -> str:
    """Return a compact, human-readable age string like '2d', '1w', '3h'."""
    delta = datetime.now(tz=UTC) - dt
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "0m"
    minutes = total_seconds // 60
    hours = minutes // 60
    days = hours // 24
    weeks = days // 7

    if weeks >= 1:
        return f"{weeks}w"
    if days >= 1:
        return f"{days}d"
    if hours >= 1:
        return f"{hours}h"
    return f"{max(minutes, 1)}m"


def _strip_ref_prefix(ref: str) -> str:
    """Remove ``refs/heads/`` prefix from a branch ref."""
    prefix = "refs/heads/"
    return ref[len(prefix):] if ref.startswith(prefix) else ref


_NOISE_PREFIXES = [
    "created from teams message", "created from teams channel",
    "from microsoft teams", "sent from",
    "hi team", "hello team", "hey team", "hi all", "hello all",
    "can someone", "could someone", "can you", "could you",
    "please help", "i need help",
    "thank you", "thanks in advance", "thanks",
]

_SIGNAL_WORDS = [
    "block", "fail", "error", "404", "500", "deploy", "pipeline",
    "migration", "missing", "broken", "regression", "upgrade", "update",
    "config", "provision", "unauthorized", "permission", "timeout", "crash",
    "hang", "reject", "deny", "denied", "certificate", "expire", "expir",
    "corrupt", "null", "exception", "rollback", "outage", "incident",
    "revert", "break",
]

_CATEGORY_DEFAULTS: dict[str, str] = {
    "Blocking Issue": "Blocking deployment issue",
    "Bug / Behavior": "Behavior issue reported",
    "PR Review": "PR needs review",
    "Feature Request": "Feature requested",
    "Support Question": "Question from user",
}


def _extract_why(
    description: str, title: str, category: str, pr_id: int | None,
) -> str:
    """Build a concise *why* string from a work-item description.

    Filters boilerplate noise, picks the most informative sentence
    (preferring those with signal words), and appends a PR reference when
    available.
    """
    desc = (description or "").strip()

    # -- fallback: description empty / mirrors title -------------------------
    desc_is_useless = (
        not desc
        or desc.lower() == title.lower()
        or (len(desc) >= 20 and title.lower().startswith(desc.lower()[:20]))
    )

    text = ""
    if not desc_is_useless:
        # Strip HTML tags and collapse whitespace runs
        cleaned = re.sub(r"<[^>]+>", " ", desc)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        lines = cleaned.splitlines()

        # Filter out URL-only lines and whitespace/punctuation-only lines
        lines = [
            ln for ln in lines
            if not re.match(r"^\s*https?://\S+\s*$", ln)
            and re.search(r"[a-zA-Z0-9]", ln)
        ]

        rejoined = "\n".join(ln.strip() for ln in lines)

        # Split into sentences, then filter noise at the sentence level
        raw_sentences = re.split(r"[.!?\n]+", rejoined)
        sentences: list[str] = []
        for s in raw_sentences:
            s = s.strip()
            if len(s) < 10:
                continue
            low = s.lower()
            if any(low.startswith(p) for p in _NOISE_PREFIXES):
                continue
            sentences.append(s)

        # Try to find a sentence with a signal word
        signal_sentence = ""
        for sentence in sentences:
            low = sentence.lower()
            if any(w in low for w in _SIGNAL_WORDS):
                signal_sentence = sentence
                break

        text = signal_sentence or (sentences[0] if sentences else "")

    # -- category-based fallback ---------------------------------------------
    if not text:
        text = _CATEGORY_DEFAULTS.get(category, "Follow up with requestor")

    # -- cleanup: capitalise first letter ------------------------------------
    text = text[0].upper() + text[1:] if text else text

    # -- cleanup: truncate to 55 chars, break on word boundary ---------------
    if len(text) > 55:
        truncated = text[:54]
        parts = truncated.rsplit(" ", 1)
        word_broken = parts[0] if len(parts) > 1 else ""
        text = (word_broken if word_broken else text[:54]) + "…"

    # -- append PR suffix ----------------------------------------------------
    if pr_id:
        pr_suffix = f" · PR #{pr_id}"
        max_text = 60 - len(pr_suffix)
        if len(text) > max_text:
            text = text[: max_text - 1] + "…"
        text += pr_suffix

    return text[:60]


# ---------------------------------------------------------------------------
# Reviewer
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Reviewer:
    """A single PR reviewer with their vote status."""

    name: str
    vote: int  # -10=rejected, -5=waiting, 0=none, 5=approved w/ suggestions, 10=approved
    email: str = ""
    has_declined: bool = False

    @property
    def vote_emoji(self) -> str:
        """Map ADO vote codes to a single emoji."""
        return {
            10: "✅",
            5: "💬",
            0: "⬜",
            -5: "⏳",
            -10: "❌",
        }.get(self.vote, "⬜")


# ---------------------------------------------------------------------------
# PullRequest
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class PullRequest:
    """Represents an Azure DevOps pull request."""

    id: int
    title: str
    status: str
    is_draft: bool
    author: str
    repo_name: str
    project: str
    source_branch: str
    target_branch: str
    created_date: datetime
    reviewers: list[Reviewer]
    labels: list[str]
    url: str
    description: str | None = None

    # -- Computed properties -------------------------------------------------

    @property
    def age(self) -> str:
        """Human-readable age since creation."""
        return _human_age(self.created_date)

    @property
    def short_source(self) -> str:
        """Source branch without ``refs/heads/`` prefix."""
        return _strip_ref_prefix(self.source_branch)

    @property
    def short_target(self) -> str:
        """Target branch without ``refs/heads/`` prefix."""
        return _strip_ref_prefix(self.target_branch)

    @property
    def copy_text(self) -> str:
        """One-liner for clipboard: ``PR #id: title (repo, source → target)``."""
        return (
            f"PR #{self.id}: {self.title} "
            f"({self.repo_name}, {self.short_source} → {self.short_target})"
        )

    @property
    def approval_style(self) -> str:
        """Return a Rich style string based on aggregate reviewer votes.

        Priority: rejection (-10) > approved (10) > suggestions (5) > none.
        """
        votes = [r.vote for r in self.reviewers if not r.has_declined]
        if any(v <= -10 for v in votes):
            return "red"
        if any(v >= 10 for v in votes):
            return "green"
        if any(v == 5 for v in votes):
            return "yellow"
        return ""

    # -- Factory / query -----------------------------------------------------

    def my_vote(self, user_email: str) -> int:
        """Return the current user's vote on this PR, or 0 if not found."""
        for reviewer in self.reviewers:
            if reviewer.email.lower() == user_email.lower():
                return reviewer.vote
        return 0

    def has_declined(self, user_email: str) -> bool:
        """Return True if the user has declined to review this PR."""
        lower = user_email.lower()
        for reviewer in self.reviewers:
            if reviewer.email.lower() == lower:
                return reviewer.has_declined
        return False

    @classmethod
    def from_az_json(cls, data: dict) -> Self:
        """Parse ``az repos pr list/show`` JSON into a :class:`PullRequest`."""
        reviewers = [
            Reviewer(
                name=r.get("displayName", r.get("uniqueName", "Unknown")),
                vote=r.get("vote", 0),
                email=r.get("uniqueName", ""),
                has_declined=r.get("hasDeclined", False),
            )
            for r in (data.get("reviewers") or [])
        ]
        labels = [lb.get("name", "") for lb in (data.get("labels") or [])]

        repo = data.get("repository") or {}
        repo_name = repo.get("name", "unknown")
        project_name = repo.get("project", {}).get("name", "")

        created_by = data.get("createdBy") or {}
        author = created_by.get("displayName", created_by.get("uniqueName", "Unknown"))

        pr_id = data["pullRequestId"]

        return cls(
            id=pr_id,
            title=data.get("title", ""),
            status=data.get("status", "unknown"),
            is_draft=data.get("isDraft", False),
            author=author,
            repo_name=repo_name,
            project=project_name,
            source_branch=data.get("sourceRefName", ""),
            target_branch=data.get("targetRefName", ""),
            created_date=_parse_ado_date(data.get("creationDate")),
            reviewers=reviewers,
            labels=labels,
            url=f"{config.ORG_URL}/{project_name}/_git/{repo_name}/pullrequest/{pr_id}",
            description=data.get("description"),
        )


# ---------------------------------------------------------------------------
# WorkItem
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class WorkItem:
    """Represents an Azure DevOps work item."""

    id: int
    title: str
    state: str
    work_item_type: str
    iteration_path: str
    area_path: str
    tags: list[str]
    changed_date: datetime
    url: str
    description: str | None = None
    priority: int | None = None
    parent_id: int | None = None
    is_context_parent: bool = False
    rev: int | None = None

    # -- Computed properties -------------------------------------------------

    @property
    def age(self) -> str:
        """Human-readable time since last change."""
        return _human_age(self.changed_date)

    @property
    def type_emoji(self) -> str:
        """Emoji for the work-item type."""
        return {
            "Bug": "🐛",
            "Task": "📋",
            "User Story": "📖",
            "Deliverable": "📦",
            "Feature": "🚀",
            "Epic": "🏔️",
            "Issue": "⚠️",
            "Scenario": "🎯",
        }.get(self.work_item_type, "📄")

    @property
    def copy_text(self) -> str:
        """One-liner for clipboard: ``WI #id: title (type, state)``."""
        return f"WI #{self.id}: {self.title} ({self.work_item_type}, {self.state})"

    @property
    def project(self) -> str:
        """The ADO project this work item belongs to.

        Derived from the first segment of ``area_path``. WIQL queries can
        return work items from projects other than the dashboard's
        configured project (e.g. when filtering by ``@Me``), so this is the
        authoritative source for "which project does this WI live in" when
        making per-work-item REST calls (allowed states, iterations,
        areas, updates).
        """
        return self.area_path.split("\\", 1)[0] if self.area_path else ""

    # -- Factory -------------------------------------------------------------

    @classmethod
    def from_az_json(cls, data: dict) -> Self:
        """Parse ``az boards work-item show`` JSON into a :class:`WorkItem`."""
        fields = data.get("fields") or {}
        wi_id = data.get("id", 0)

        raw_tags = fields.get("System.Tags") or ""
        tags = [t.strip() for t in raw_tags.split(";") if t.strip()] if raw_tags else []

        # System.Parent is a calculated field (int) available in ADO Services.
        raw_parent = fields.get("System.Parent")
        parent_id = int(raw_parent) if raw_parent else None

        # Concurrency token. ADO returns ``rev`` at the top level of the
        # work-item payload; older WIQL responses surface it as
        # ``System.Rev`` inside ``fields``. Prefer the top-level value.
        raw_rev = data.get("rev")
        if raw_rev is None:
            raw_rev = fields.get("System.Rev")
        rev = int(raw_rev) if raw_rev is not None else None

        return cls(
            id=wi_id,
            title=fields.get("System.Title", ""),
            state=fields.get("System.State", "Unknown"),
            work_item_type=fields.get("System.WorkItemType", "Unknown"),
            iteration_path=fields.get("System.IterationPath", ""),
            area_path=fields.get("System.AreaPath", ""),
            tags=tags,
            changed_date=_parse_ado_date(fields.get("System.ChangedDate")),
            url=config.work_item_url(wi_id),
            description=fields.get("System.Description"),
            priority=fields.get("Microsoft.VSTS.Common.Priority"),
            parent_id=parent_id,
            rev=rev,
        )


# ---------------------------------------------------------------------------
# TriageItem
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class TriageItem:
    """An item from a triage board."""

    id: int
    title: str
    description: str
    created_date: str  # "YYYY-MM-DD" string from the script
    age_days: int
    assigned_to: str
    pr_id: int | None
    tags: str
    priority: int | None
    work_item_type: str
    board: str = ""
    category: str = ""  # filled in after categorisation
    urgency_rank: int = 0
    ai_why: str = ""
    ai_priority: int | None = None

    @property
    def age(self) -> str:
        """Human-readable age string like '2d' or '3w'."""
        if self.age_days < 0:
            return "?"
        if self.age_days >= 7:
            return f"{self.age_days // 7}w"
        return f"{self.age_days}d"

    @property
    def type_emoji(self) -> str:
        """Emoji for the work-item type."""
        return {
            "Bug": "🐛",
            "Task": "📋",
            "User Story": "📖",
            "Deliverable": "📦",
            "Feature": "🚀",
        }.get(self.work_item_type, "📄")

    @property
    def priority_label(self) -> str:
        """Short priority label like 'P1', 'P2', etc."""
        return {1: "P1", 2: "P2", 3: "P3", 4: "P4"}.get(self.priority or 0, "—")

    @property
    def why(self) -> str:
        """Brief context for the triage table Why column."""
        if self.ai_why:
            return self.ai_why[:60]
        return _extract_why(self.description, self.title, self.category, self.pr_id)

    @property
    def category_emoji(self) -> str:
        """Emoji for the triage category."""
        return {
            "Blocking Issue": "🚨",
            "Bug / Behavior": "🐛",
            "PR Review": "🔍",
            "Feature Request": "✨",
            "Support Question": "❓",
        }.get(self.category, "📄")

    @property
    def effective_priority(self) -> int:
        """Priority for grouping (uses AI priority, then ADO priority, then category default)."""
        if self.ai_priority and 1 <= self.ai_priority <= 4:
            return self.ai_priority
        if self.priority and 1 <= self.priority <= 4:
            return self.priority
        return {
            "Blocking Issue": 1,
            "Bug / Behavior": 2,
            "PR Review": 2,
            "Feature Request": 3,
            "Support Question": 3,
        }.get(self.category, 3)

    @property
    def copy_text(self) -> str:
        """One-liner for clipboard: ``Triage #id: title (type, priority)``."""
        return f"Triage #{self.id}: {self.title} ({self.work_item_type}, {self.priority_label})"

    @property
    def url(self) -> str:
        """Browser URL for this work item in ADO."""
        return config.work_item_url(self.id)

    @classmethod
    def from_json(cls, data: dict) -> Self:
        """Parse a dict from the Get-TriageItems.ps1 JSON output."""
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            created_date=data.get("createdDate", ""),
            age_days=data.get("ageDays", -1),
            assigned_to=data.get("assignedTo", "Unassigned"),
            pr_id=data.get("prId"),
            tags=data.get("tags", ""),
            priority=data.get("priority"),
            work_item_type=data.get("workItemType", ""),
            board=data.get("board", ""),
        )


# ---------------------------------------------------------------------------
# AI triage response models
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AITriageResult:
    """AI-assigned triage data for a single work item."""

    id: int
    category: str
    priority: int
    why: str


@dataclass(frozen=True, slots=True)
class TriageAnalysis:
    """Complete AI triage analysis response."""

    items: list[AITriageResult]
    action_plan: str

    @classmethod
    def from_json(cls, data: dict) -> Self:
        """Parse an AI response dict into a :class:`TriageAnalysis`."""
        items = [
            AITriageResult(
                id=item.get("id", 0),
                category=item.get("category", ""),
                priority=item.get("priority", 3),
                why=item.get("why", ""),
            )
            for item in data.get("items", [])
        ]
        return cls(items=items, action_plan=data.get("action_plan", ""))


# ---------------------------------------------------------------------------
# CopilotSession
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CopilotSession:
    """A GitHub Copilot CLI session from local session-state."""

    id: str
    summary: str
    cwd: str
    git_root: str
    branch: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    pid: int | None
    intent: str
    event_count: int
    copilot_version: str

    # -- Computed properties -------------------------------------------------

    @property
    def age(self) -> str:
        """Human-readable age since creation."""
        return _human_age(self.created_at)

    @property
    def last_active(self) -> str:
        """Human-readable time since last update."""
        return _human_age(self.updated_at)

    @property
    def short_cwd(self) -> str:
        """Last 2 path segments of ``cwd`` for compact display."""
        parts = self.cwd.replace("\\", "/").rstrip("/").rsplit("/", 2)
        return "/".join(parts[-2:]) if len(parts) >= 2 else self.cwd

    @property
    def status_emoji(self) -> str:
        """Status indicator: 🟢 active, ⚪ updated <24 h, 🔴 stale."""
        if self.is_active:
            return "🟢"
        delta = datetime.now(tz=UTC) - self.updated_at
        if delta.total_seconds() < 86_400:
            return "⚪"
        return "🔴"

    @property
    def copy_text(self) -> str:
        """One-liner for clipboard: ``Session <id[:8]>: summary (branch, short_cwd)``."""
        label = self.summary or self.intent or "(no summary)"
        return f"Session {self.id[:8]}: {label} ({self.branch}, {self.short_cwd})"

    @property
    def url(self) -> str:
        """Local ``cwd`` path (for the open-in-browser action)."""
        return self.cwd
