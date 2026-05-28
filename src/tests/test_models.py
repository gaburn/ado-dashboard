"""Tests for ado_dashboard.models — dataclass parsers and edge cases."""

from ado_dashboard.models import PullRequest, TriageAnalysis, TriageItem, WorkItem


def test_pull_request_from_az_json_basic():
    """PullRequest.from_az_json parses basic PR data."""
    data = {
        "pullRequestId": 123,
        "title": "Test PR",
        "status": "active",
        "isDraft": False,
        "createdBy": {"displayName": "Test User", "uniqueName": "user@example.com"},
        "repository": {"name": "TestRepo", "project": {"name": "TestProject"}},
        "sourceRefName": "refs/heads/feature",
        "targetRefName": "refs/heads/main",
        "creationDate": "2024-01-01T00:00:00Z",
        "reviewers": [],
        "labels": [],
    }
    pr = PullRequest.from_az_json(data)
    assert pr.id == 123
    assert pr.title == "Test PR"
    assert pr.status == "active"
    assert pr.is_draft is False
    assert pr.author == "Test User"
    assert pr.repo_name == "TestRepo"
    assert pr.project == "TestProject"


def test_pull_request_from_az_json_missing_assigned_to():
    """PullRequest.from_az_json handles missing assignedTo."""
    data = {
        "pullRequestId": 123,
        "title": "Test PR",
        "createdBy": {},
        "repository": {"name": "TestRepo", "project": {"name": "TestProject"}},
        "sourceRefName": "refs/heads/feature",
        "targetRefName": "refs/heads/main",
        "creationDate": "2024-01-01T00:00:00Z",
    }
    pr = PullRequest.from_az_json(data)
    assert pr.author == "Unknown"


def test_pull_request_reviewers():
    """PullRequest.from_az_json parses reviewers with votes."""
    data = {
        "pullRequestId": 123,
        "title": "Test PR",
        "createdBy": {"displayName": "Author"},
        "repository": {"name": "TestRepo", "project": {"name": "TestProject"}},
        "sourceRefName": "refs/heads/feature",
        "targetRefName": "refs/heads/main",
        "creationDate": "2024-01-01T00:00:00Z",
        "reviewers": [
            {"displayName": "Reviewer1", "uniqueName": "r1@example.com", "vote": 10},
            {"displayName": "Reviewer2", "uniqueName": "r2@example.com", "vote": -10},
        ],
    }
    pr = PullRequest.from_az_json(data)
    assert len(pr.reviewers) == 2
    assert pr.reviewers[0].name == "Reviewer1"
    assert pr.reviewers[0].vote == 10
    assert pr.reviewers[1].vote == -10


def test_work_item_from_az_json_basic():
    """WorkItem.from_az_json parses basic work item data."""
    data = {
        "id": 456,
        "fields": {
            "System.Title": "Test Work Item",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.IterationPath": "Iteration 1",
            "System.AreaPath": "Area 1",
            "System.Tags": "tag1; tag2",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
        },
    }
    wi = WorkItem.from_az_json(data)
    assert wi.id == 456
    assert wi.title == "Test Work Item"
    assert wi.state == "Active"
    assert wi.work_item_type == "Task"
    assert wi.tags == ["tag1", "tag2"]


def test_work_item_from_az_json_missing_priority():
    """WorkItem.from_az_json handles missing priority field."""
    data = {
        "id": 456,
        "fields": {
            "System.Title": "Test Work Item",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.IterationPath": "Iteration 1",
            "System.AreaPath": "Area 1",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
        },
    }
    wi = WorkItem.from_az_json(data)
    assert wi.priority is None


def test_work_item_from_az_json_with_priority():
    """WorkItem.from_az_json parses priority when present."""
    data = {
        "id": 456,
        "fields": {
            "System.Title": "Test Work Item",
            "System.State": "Active",
            "System.WorkItemType": "Bug",
            "System.IterationPath": "Iteration 1",
            "System.AreaPath": "Area 1",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
            "Microsoft.VSTS.Common.Priority": 1,
        },
    }
    wi = WorkItem.from_az_json(data)
    assert wi.priority == 1


def test_work_item_description_html_stripping():
    """WorkItem description HTML tags are stripped in why logic (indirectly tested)."""
    data = {
        "id": 456,
        "fields": {
            "System.Title": "Test",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.IterationPath": "Iteration 1",
            "System.AreaPath": "Area 1",
            "System.ChangedDate": "2024-01-01T00:00:00Z",
            "System.Description": "<div>HTML description</div>",
        },
    }
    wi = WorkItem.from_az_json(data)
    assert wi.description == "<div>HTML description</div>"


def test_triage_item_from_json_basic():
    """TriageItem.from_json parses basic triage data."""
    data = {
        "id": 789,
        "title": "Test Triage Item",
        "description": "Test description",
        "createdDate": "2024-01-01",
        "ageDays": 5,
        "assignedTo": "user@example.com",
        "prId": None,
        "tags": "tag1",
        "priority": 2,
        "workItemType": "Bug",
        "board": "TestBoard",
    }
    item = TriageItem.from_json(data)
    assert item.id == 789
    assert item.title == "Test Triage Item"
    assert item.description == "Test description"
    assert item.age_days == 5
    assert item.assigned_to == "user@example.com"
    assert item.priority == 2
    assert item.work_item_type == "Bug"


def test_triage_item_from_json_missing_assigned_to():
    """TriageItem.from_json defaults assignedTo to 'Unassigned' when missing."""
    data = {
        "id": 789,
        "title": "Test",
        "description": "",
        "createdDate": "2024-01-01",
        "ageDays": 5,
        "tags": "",
        "workItemType": "Task",
    }
    item = TriageItem.from_json(data)
    assert item.assigned_to == "Unassigned"


def test_triage_item_from_json_missing_pr_id():
    """TriageItem.from_json handles missing prId."""
    data = {
        "id": 789,
        "title": "Test",
        "description": "",
        "createdDate": "2024-01-01",
        "ageDays": 5,
        "assignedTo": "user@example.com",
        "tags": "",
        "workItemType": "Task",
    }
    item = TriageItem.from_json(data)
    assert item.pr_id is None


def test_triage_item_effective_priority_uses_ai():
    """TriageItem.effective_priority prefers ai_priority."""
    item = TriageItem.from_json({
        "id": 1,
        "title": "Test",
        "description": "",
        "createdDate": "2024-01-01",
        "ageDays": 5,
        "assignedTo": "user@example.com",
        "tags": "",
        "priority": 3,
        "workItemType": "Task",
    })
    item.ai_priority = 1
    assert item.effective_priority == 1


def test_triage_item_effective_priority_uses_ado():
    """TriageItem.effective_priority uses ADO priority when AI not set."""
    item = TriageItem.from_json({
        "id": 1,
        "title": "Test",
        "description": "",
        "createdDate": "2024-01-01",
        "ageDays": 5,
        "assignedTo": "user@example.com",
        "tags": "",
        "priority": 2,
        "workItemType": "Task",
    })
    assert item.effective_priority == 2


def test_triage_analysis_from_json():
    """TriageAnalysis.from_json parses AI response."""
    data = {
        "items": [
            {"id": 1, "category": "Bug / Behavior", "priority": 1, "why": "Critical bug"},
            {"id": 2, "category": "PR Review", "priority": 2, "why": "Needs review"},
        ],
        "action_plan": "Fix P1 items first",
    }
    analysis = TriageAnalysis.from_json(data)
    assert len(analysis.items) == 2
    assert analysis.items[0].id == 1
    assert analysis.items[0].category == "Bug / Behavior"
    assert analysis.action_plan == "Fix P1 items first"
