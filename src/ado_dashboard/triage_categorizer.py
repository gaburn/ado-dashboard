"""Pure-function module that categorizes triage items and groups them by priority."""

from __future__ import annotations

import re

from ado_dashboard.models import TriageAnalysis, TriageItem

# ---------------------------------------------------------------------------
# Category keywords (compiled once)
# ---------------------------------------------------------------------------
_BLOCKING_PATTERNS: re.Pattern[str] = re.compile(
    r"block|fail|broke|404|500|outage|pipeline error"
    r"|can'?t deploy|cannot deploy|production down|not found",
    re.IGNORECASE,
)

_PR_TITLE_PATTERNS: re.Pattern[str] = re.compile(
    r"pr review|pull request",
    re.IGNORECASE,
)

_BUG_PATTERNS: re.Pattern[str] = re.compile(
    r"bug|not working|unexpected|regression|incorrect|wrong|error",
    re.IGNORECASE,
)

_FEATURE_PATTERNS: re.Pattern[str] = re.compile(
    r"feature|new resource|new model|add support|capability|enhancement",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Category defaults for priority & urgency base scores
# ---------------------------------------------------------------------------
_DEFAULT_PRIORITY: dict[str, int] = {
    "Blocking Issue": 1,
    "PR Review": 2,
    "Bug / Behavior": 2,
    "Feature Request": 3,
    "Support Question": 3,
}

_URGENCY_BASE: dict[int, int] = {1: 400, 2: 300, 3: 200, 4: 100}

_VALID_CATEGORIES: set[str] = set(_DEFAULT_PRIORITY)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _text_blob(item: TriageItem) -> str:
    """Combine title and description into a single searchable string."""
    return f"{item.title} {item.description or ''}"


def _classify(item: TriageItem) -> str:
    """Return the category name for *item* (first-match wins)."""
    blob = _text_blob(item)

    if _BLOCKING_PATTERNS.search(blob):
        return "Blocking Issue"

    if item.pr_id is not None or _PR_TITLE_PATTERNS.search(item.title):
        return "PR Review"

    if item.work_item_type == "Bug" or _BUG_PATTERNS.search(blob):
        return "Bug / Behavior"

    if item.work_item_type in ("Feature", "User Story") or _FEATURE_PATTERNS.search(blob):
        return "Feature Request"

    return "Support Question"


def _effective_priority(item: TriageItem) -> int:
    """Use ADO priority when available; otherwise fall back to category default."""
    if item.priority is not None and 1 <= item.priority <= 4:
        return item.priority
    return _DEFAULT_PRIORITY.get(item.category, 3)


def _urgency_rank(item: TriageItem, priority: int) -> int:
    """Calculate urgency rank = base_score + age_bonus."""
    base = _URGENCY_BASE.get(priority, 100)
    age_bonus = min(max(item.age_days, 0), 90)
    return base + age_bonus


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def categorize_triage_items(items: list[TriageItem]) -> dict[int, list[TriageItem]]:
    """Categorize *items* in place and return them grouped by priority (1-4).

    Each item's ``.category`` and ``.urgency_rank`` fields are mutated.
    The returned dict omits priority keys that have no items, and each
    list is sorted by ``urgency_rank`` descending (most urgent first).
    """
    buckets: dict[int, list[TriageItem]] = {}

    for item in items:
        item.category = _classify(item)
        priority = _effective_priority(item)
        item.urgency_rank = _urgency_rank(item, priority)
        buckets.setdefault(priority, []).append(item)

    # Sort each bucket by urgency_rank descending
    for priority in buckets:
        buckets[priority].sort(key=lambda it: it.urgency_rank, reverse=True)

    return buckets


def generate_action_plan(groups: dict[int, list[TriageItem]]) -> str:
    """Build a deterministic 2-3 line action plan from categorized triage groups.

    This provides an always-available recommendation even without AI.
    If AI is enabled it will overwrite the plan with a richer version later.
    """
    all_items: list[TriageItem] = [
        item for bucket in groups.values() for item in bucket
    ]
    if not all_items:
        return ""

    # Count items by category across all priorities.
    by_category: dict[str, list[TriageItem]] = {}
    for item in all_items:
        by_category.setdefault(item.category, []).append(item)

    p1_items = groups.get(1, [])
    p2_items = groups.get(2, [])

    lines: list[str] = []

    # --- Line 1: highest-priority blockers ---
    if p1_items:
        previews = [f"#{it.id} {it.title[:30]}" for it in p1_items[:3]]
        lines.append(f"• P1 blockers first — {len(p1_items)} critical items: {', '.join(previews)}")
    elif p2_items:
        previews = [f"#{it.id} {it.title[:30]}" for it in p2_items[:3]]
        lines.append(f"• Start with P2 — {len(p2_items)} high-priority items: {', '.join(previews)}")

    # --- Line 2: PR reviews ---
    pr_items = by_category.get("PR Review", [])
    if pr_items:
        parts: list[str] = []
        for it in pr_items:
            label = f"PR !{it.pr_id}" if it.pr_id is not None else f"#{it.id}"
            parts.append(label)
        doc_prs = [it for it in pr_items if "doc" in (it.title + (it.description or "")).lower()]
        suffix = ""
        if doc_prs:
            suffix = " (docs PRs are quick wins)"
        lines.append(f"• Batch PR reviews — {len(pr_items)} PRs: {', '.join(parts)}{suffix}")

    # --- Line 3: support questions ---
    support_items = by_category.get("Support Question", [])
    if support_items:
        lines.append(f"• Quick answers — {len(support_items)} support questions")

    return "\n".join(lines[:3])


def apply_ai_analysis(items: list[TriageItem], analysis: TriageAnalysis) -> dict[int, list[TriageItem]]:
    """Apply AI analysis results to existing triage items and regroup by priority.

    Merges AI-assigned category, priority, and why into items that were
    previously categorised by the rule-based ``categorize_triage_items``.
    Items not found in the AI response keep their original values.
    """
    lookup = {result.id: result for result in analysis.items}

    for item in items:
        result = lookup.get(item.id)
        if result is None:
            continue
        if result.category in _VALID_CATEGORIES:
            item.category = result.category
        if result.priority and 1 <= result.priority <= 4:
            item.ai_priority = result.priority
        if result.why:
            item.ai_why = result.why

    # Recompute urgency_rank using effective_priority (which now reflects AI)
    buckets: dict[int, list[TriageItem]] = {}
    for item in items:
        priority = item.effective_priority
        item.urgency_rank = _urgency_rank(item, priority)
        buckets.setdefault(priority, []).append(item)

    for priority in buckets:
        buckets[priority].sort(key=lambda it: it.urgency_rank, reverse=True)

    return buckets
