"""Tests for ado_dashboard.triage_categorizer — pure categorization logic."""

from ado_dashboard import triage_categorizer
from ado_dashboard.models import TriageItem, TriageAnalysis, AITriageResult


def _make_item(
    title="Test Item",
    description="",
    work_item_type="Task",
    pr_id=None,
    priority=None,
    age_days=5,
):
    """Helper to create a TriageItem for testing."""
    return TriageItem(
        id=1,
        title=title,
        description=description,
        created_date="2024-01-01",
        age_days=age_days,
        assigned_to="user@example.com",
        pr_id=pr_id,
        tags="",
        priority=priority,
        work_item_type=work_item_type,
        board="TestBoard",
    )


def test_categorize_blocking_issue():
    """Item with blocking keywords is categorized as Blocking Issue."""
    item = _make_item(title="Pipeline blocked by 500 error")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "Blocking Issue"


def test_categorize_pr_review_by_pr_id():
    """Item with pr_id is categorized as PR Review."""
    item = _make_item(title="Review my code", pr_id=123)
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "PR Review"


def test_categorize_pr_review_by_title():
    """Item with 'PR review' in title is categorized as PR Review."""
    item = _make_item(title="PR review needed for feature X")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "PR Review"


def test_categorize_bug_by_type():
    """Item with work_item_type='Bug' is categorized as Bug / Behavior."""
    item = _make_item(work_item_type="Bug", title="Normal bug report")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "Bug / Behavior"


def test_categorize_bug_by_keywords():
    """Item with bug keywords is categorized as Bug / Behavior."""
    item = _make_item(title="This is not working correctly")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "Bug / Behavior"


def test_categorize_feature_by_type():
    """Item with work_item_type='Feature' is categorized as Feature Request."""
    item = _make_item(work_item_type="Feature", title="Add new capability")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "Feature Request"


def test_categorize_feature_by_keywords():
    """Item with feature keywords is categorized as Feature Request."""
    item = _make_item(title="New feature: add support for X")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "Feature Request"


def test_categorize_support_question():
    """Item without specific keywords is categorized as Support Question."""
    item = _make_item(title="How do I configure this?")
    triage_categorizer.categorize_triage_items([item])
    assert item.category == "Support Question"


def test_categorize_priority_p1():
    """Item with priority=1 lands in P1 bucket."""
    item = _make_item(priority=1)
    result = triage_categorizer.categorize_triage_items([item])
    assert 1 in result
    assert item in result[1]


def test_categorize_priority_p2():
    """Item with priority=2 lands in P2 bucket."""
    item = _make_item(priority=2)
    result = triage_categorizer.categorize_triage_items([item])
    assert 2 in result
    assert item in result[2]


def test_categorize_priority_p3():
    """Item with priority=3 lands in P3 bucket."""
    item = _make_item(priority=3)
    result = triage_categorizer.categorize_triage_items([item])
    assert 3 in result
    assert item in result[3]


def test_categorize_priority_p4():
    """Item with priority=4 lands in P4 bucket."""
    item = _make_item(priority=4)
    result = triage_categorizer.categorize_triage_items([item])
    assert 4 in result
    assert item in result[4]


def test_categorize_urgency_rank_set():
    """Item urgency_rank is set after categorization."""
    item = _make_item(priority=1)
    triage_categorizer.categorize_triage_items([item])
    assert item.urgency_rank > 0


def test_categorize_sorts_by_urgency():
    """Items in same bucket are sorted by urgency_rank descending."""
    item1 = _make_item(priority=2, age_days=1)
    item2 = _make_item(priority=2, age_days=30)
    result = triage_categorizer.categorize_triage_items([item1, item2])
    # item2 should be first (older = higher urgency)
    assert result[2][0].age_days == 30
    assert result[2][1].age_days == 1


def test_generate_action_plan_empty():
    """generate_action_plan returns empty string for empty input."""
    plan = triage_categorizer.generate_action_plan({})
    assert plan == ""


def test_generate_action_plan_p1_items():
    """generate_action_plan mentions P1 items when present."""
    item = _make_item(priority=1, title="Critical bug")
    groups = {1: [item]}
    plan = triage_categorizer.generate_action_plan(groups)
    assert "P1" in plan
    assert "critical" in plan.lower()


def test_generate_action_plan_pr_review():
    """generate_action_plan mentions PR reviews when present."""
    item = _make_item(pr_id=123, title="Review PR")
    item.category = "PR Review"
    groups = {2: [item]}
    plan = triage_categorizer.generate_action_plan(groups)
    assert "PR" in plan


def test_generate_action_plan_support_questions():
    """generate_action_plan mentions support questions when present."""
    item = _make_item(title="How do I...")
    item.category = "Support Question"
    groups = {3: [item]}
    plan = triage_categorizer.generate_action_plan(groups)
    assert "support" in plan.lower() or "question" in plan.lower()


def test_apply_ai_analysis():
    """apply_ai_analysis merges AI results into items."""
    item = _make_item()
    item.category = "Support Question"
    analysis = TriageAnalysis(
        items=[
            AITriageResult(id=1, category="Bug / Behavior", priority=1, why="Test reason")
        ],
        action_plan="Test action plan",
    )
    result = triage_categorizer.apply_ai_analysis([item], analysis)
    assert item.category == "Bug / Behavior"
    assert item.ai_priority == 1
    assert item.ai_why == "Test reason"
    assert 1 in result


def test_apply_ai_analysis_invalid_category_ignored():
    """apply_ai_analysis ignores invalid categories."""
    item = _make_item()
    item.category = "Support Question"
    analysis = TriageAnalysis(
        items=[
            AITriageResult(id=1, category="Invalid Category", priority=1, why="Test")
        ],
        action_plan="",
    )
    triage_categorizer.apply_ai_analysis([item], analysis)
    assert item.category == "Support Question"  # unchanged


def test_apply_ai_analysis_invalid_priority_ignored():
    """apply_ai_analysis ignores invalid priority values."""
    item = _make_item()
    item.category = "Support Question"
    analysis = TriageAnalysis(
        items=[
            AITriageResult(id=1, category="Bug / Behavior", priority=99, why="Test")
        ],
        action_plan="",
    )
    triage_categorizer.apply_ai_analysis([item], analysis)
    assert item.ai_priority is None or item.ai_priority != 99
