"""Tests for demo mode — fixture data shapes, demo clients, and factory behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from ado_dashboard.demo import DemoAdoClient, DemoSessionClient, DemoTriageClient
from ado_dashboard.demo.fixtures import (
    DEMO_ORG_URL,
    DEMO_PROJECT,
    DEMO_USER_EMAIL,
    get_my_prs,
    get_reviewing_prs,
    get_sessions,
    get_triage_items,
    get_work_items,
)
from ado_dashboard.models import CopilotSession, PullRequest, TriageItem, WorkItem

# ---------------------------------------------------------------------------
# Fixture data: model shapes
# ---------------------------------------------------------------------------

class TestFixtureShapes:
    def test_my_prs_returns_pull_requests(self):
        prs = get_my_prs()
        assert len(prs) >= 4
        for pr in prs:
            assert isinstance(pr, PullRequest)

    def test_my_pr_fields_populated(self):
        prs = get_my_prs()
        for pr in prs:
            assert pr.id > 0
            assert pr.title
            assert pr.repo_name
            assert pr.project == DEMO_PROJECT
            assert pr.source_branch.startswith("refs/heads/")
            assert pr.target_branch.startswith("refs/heads/")
            assert pr.author
            assert pr.url.startswith(DEMO_ORG_URL)

    def test_my_prs_have_mixed_draft_states(self):
        prs = get_my_prs()
        drafts = [p for p in prs if p.is_draft]
        non_drafts = [p for p in prs if not p.is_draft]
        assert drafts, "Expected at least one draft PR"
        assert non_drafts, "Expected at least one non-draft PR"

    def test_reviewing_prs_returns_pull_requests(self):
        prs = get_reviewing_prs()
        assert len(prs) >= 5
        for pr in prs:
            assert isinstance(pr, PullRequest)

    def test_reviewing_prs_have_varied_vote_states(self):
        prs = get_reviewing_prs()
        all_votes = [r.vote for pr in prs for r in pr.reviewers]
        # Expect multiple distinct vote values (10=approved, 0=no vote, -10=rejected, etc.)
        unique_votes = set(all_votes)
        assert len(unique_votes) >= 3, f"Expected varied votes, got {unique_votes}"

    def test_reviewing_prs_demo_user_is_reviewer(self):
        """Every reviewing PR should include the demo user as a reviewer."""
        prs = get_reviewing_prs()
        for pr in prs:
            reviewer_emails = {r.email.lower() for r in pr.reviewers}
            assert DEMO_USER_EMAIL.lower() in reviewer_emails, (
                f"PR #{pr.id} does not include demo user as reviewer"
            )

    def test_work_items_returns_work_items(self):
        items = get_work_items()
        assert len(items) >= 10
        for wi in items:
            assert isinstance(wi, WorkItem)

    def test_work_items_have_varied_types(self):
        items = get_work_items()
        types = {wi.work_item_type for wi in items}
        # Must cover multiple types
        assert "Bug" in types
        assert "Task" in types
        assert "User Story" in types
        assert "Epic" in types or "Feature" in types

    def test_work_items_have_varied_states(self):
        items = get_work_items()
        states = {wi.state for wi in items}
        assert len(states) >= 2, f"Expected varied states, got {states}"

    def test_work_items_have_hierarchy(self):
        items = get_work_items()
        items_with_parents = [wi for wi in items if wi.parent_id is not None]
        assert items_with_parents, "Expected some work items with parent_id set"

    def test_work_items_have_context_parents(self):
        items = get_work_items()
        context_parents = [wi for wi in items if wi.is_context_parent]
        assert context_parents, "Expected some context-parent work items"

    def test_triage_items_returns_triage_items(self):
        items = get_triage_items()
        assert len(items) >= 5
        for item in items:
            assert isinstance(item, TriageItem)

    def test_triage_items_have_categories(self):
        items = get_triage_items()
        categories = {item.category for item in items}
        assert len(categories) >= 3

    def test_triage_items_have_varied_priorities(self):
        items = get_triage_items()
        priorities = {item.priority for item in items if item.priority}
        assert len(priorities) >= 2

    def test_sessions_returns_copilot_sessions(self):
        sessions = get_sessions()
        assert len(sessions) >= 4
        for s in sessions:
            assert isinstance(s, CopilotSession)

    def test_sessions_have_active_and_inactive(self):
        sessions = get_sessions()
        active = [s for s in sessions if s.is_active]
        inactive = [s for s in sessions if not s.is_active]
        assert active, "Expected at least one active session"
        assert inactive, "Expected at least one inactive session"

    def test_sessions_have_summaries_and_intents(self):
        sessions = get_sessions()
        for s in sessions:
            assert s.summary
            assert s.cwd
            assert s.branch


# ---------------------------------------------------------------------------
# Demo clients: method return types
# ---------------------------------------------------------------------------

class TestDemoAdoClient:
    def test_fetch_my_prs_returns_list_of_prs(self):
        client = DemoAdoClient()
        prs = asyncio.run(client.fetch_my_prs())
        assert isinstance(prs, list)
        assert all(isinstance(p, PullRequest) for p in prs)

    def test_fetch_reviewing_prs_returns_list_of_prs(self):
        client = DemoAdoClient()
        prs = asyncio.run(client.fetch_reviewing_prs())
        assert isinstance(prs, list)
        assert all(isinstance(p, PullRequest) for p in prs)

    def test_fetch_work_items_returns_list_of_work_items(self):
        client = DemoAdoClient()
        items = asyncio.run(client.fetch_work_items_with_hierarchy())
        assert isinstance(items, list)
        assert all(isinstance(wi, WorkItem) for wi in items)

    def test_fetch_my_prs_non_empty(self):
        client = DemoAdoClient()
        prs = asyncio.run(client.fetch_my_prs())
        assert len(prs) >= 4

    def test_fetch_reviewing_prs_non_empty(self):
        client = DemoAdoClient()
        prs = asyncio.run(client.fetch_reviewing_prs())
        assert len(prs) >= 5

    def test_fetch_work_items_non_empty(self):
        client = DemoAdoClient()
        items = asyncio.run(client.fetch_work_items_with_hierarchy())
        assert len(items) >= 10


class TestDemoTriageClient:
    def test_fetch_triage_items_returns_list_of_triage_items(self):
        client = DemoTriageClient()
        items = asyncio.run(client.fetch_triage_items())
        assert isinstance(items, list)
        assert all(isinstance(i, TriageItem) for i in items)

    def test_fetch_triage_items_non_empty(self):
        client = DemoTriageClient()
        items = asyncio.run(client.fetch_triage_items())
        assert len(items) >= 5

    def test_fetch_triage_ignores_board_arg(self):
        client = DemoTriageClient()
        items_a = asyncio.run(client.fetch_triage_items(board="board-a"))
        items_b = asyncio.run(client.fetch_triage_items(board="board-b"))
        assert len(items_a) == len(items_b)


class TestDemoSessionClient:
    def test_fetch_sessions_returns_list_of_sessions(self):
        client = DemoSessionClient()
        sessions = asyncio.run(client.fetch_sessions())
        assert isinstance(sessions, list)
        assert all(isinstance(s, CopilotSession) for s in sessions)

    def test_fetch_sessions_non_empty(self):
        client = DemoSessionClient()
        sessions = asyncio.run(client.fetch_sessions())
        assert len(sessions) >= 4


# ---------------------------------------------------------------------------
# Factory: demo=True returns demo clients
# ---------------------------------------------------------------------------

class TestDemoFactory:
    def test_demo_ado_client_returned_when_demo_mode(self):
        from ado_dashboard import config
        original = config.DEMO_MODE
        try:
            config.DEMO_MODE = True
            from ado_dashboard.screens.dashboard import _demo_ado
            client = _demo_ado()
            assert isinstance(client, DemoAdoClient)
        finally:
            config.DEMO_MODE = original

    def test_real_ado_client_not_returned_when_demo_mode_off(self):
        from ado_dashboard import config
        original = config.DEMO_MODE
        try:
            config.DEMO_MODE = False
            from ado_dashboard.screens.dashboard import _demo_ado
            client = _demo_ado()
            assert client is None
        finally:
            config.DEMO_MODE = original

    def test_demo_triage_client_returned_when_demo_mode(self):
        from ado_dashboard import config
        original = config.DEMO_MODE
        try:
            config.DEMO_MODE = True
            from ado_dashboard.screens.dashboard import _demo_triage
            client = _demo_triage()
            assert isinstance(client, DemoTriageClient)
        finally:
            config.DEMO_MODE = original

    def test_demo_session_client_returned_when_demo_mode(self):
        from ado_dashboard import config
        original = config.DEMO_MODE
        try:
            config.DEMO_MODE = True
            from ado_dashboard.screens.dashboard import _demo_session
            client = _demo_session()
            assert isinstance(client, DemoSessionClient)
        finally:
            config.DEMO_MODE = original


# ---------------------------------------------------------------------------
# No subprocess invocations in demo clients
# ---------------------------------------------------------------------------

class TestDemoNoSubprocess:
    """Demo clients must never invoke subprocess or az CLI."""

    def test_demo_ado_client_no_subprocess(self):
        with patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen, \
             patch("asyncio.create_subprocess_exec") as mock_exec:
            client = DemoAdoClient()
            asyncio.run(client.fetch_my_prs())
            asyncio.run(client.fetch_reviewing_prs())
            asyncio.run(client.fetch_work_items_with_hierarchy())
            assert mock_run.call_count == 0
            assert mock_popen.call_count == 0
            assert mock_exec.call_count == 0

    def test_demo_triage_client_no_subprocess(self):
        with patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen, \
             patch("asyncio.create_subprocess_exec") as mock_exec:
            client = DemoTriageClient()
            asyncio.run(client.fetch_triage_items())
            assert mock_run.call_count == 0
            assert mock_popen.call_count == 0
            assert mock_exec.call_count == 0

    def test_demo_session_client_no_subprocess(self):
        with patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen, \
             patch("asyncio.create_subprocess_exec") as mock_exec:
            client = DemoSessionClient()
            asyncio.run(client.fetch_sessions())
            assert mock_run.call_count == 0
            assert mock_popen.call_count == 0
            assert mock_exec.call_count == 0


# ---------------------------------------------------------------------------
# Fixture content: no obviously-internal strings
# ---------------------------------------------------------------------------

_INTERNAL_STRINGS = [
    "microsoft.com",
    "corp.microsoft",
    "redmond",
    "msft",
    "@microsoft",
    "internal",
    "azure.com/microsoft",
    "1es.",
    "aka.ms",
]


class TestFixtureContentSafety:
    """Fixture data must not contain strings that could be mistaken for real M$ content."""

    def _all_fixture_text(self) -> str:
        parts: list[str] = []
        for pr in get_my_prs() + get_reviewing_prs():
            parts += [pr.title, pr.author, pr.repo_name, pr.url]
            for r in pr.reviewers:
                parts += [r.name, r.email]
        for wi in get_work_items():
            parts += [wi.title, wi.url, wi.area_path, wi.iteration_path]
        for item in get_triage_items():
            parts += [item.title, item.description, item.assigned_to]
        for s in get_sessions():
            parts += [s.summary, s.cwd, s.branch, s.intent]
        return "\n".join(parts).lower()

    def test_no_internal_microsoft_strings(self):
        text = self._all_fixture_text()
        for bad in _INTERNAL_STRINGS:
            assert bad.lower() not in text, (
                f"Fixture data contains internal string: {bad!r}"
            )

    def test_org_url_is_fictional(self):
        text = self._all_fixture_text()
        assert "middle-earth" in text, "Expected middle-earth org in fixture data"
        assert "dev.azure.com/middle-earth" in text

    def test_emails_use_fictional_domain(self):
        all_emails: list[str] = []
        for pr in get_my_prs() + get_reviewing_prs():
            all_emails.extend(r.email for r in pr.reviewers)
        all_emails.append(DEMO_USER_EMAIL)
        for email in all_emails:
            if email:
                assert "middle-earth.example" in email, (
                    f"Fixture email should use fictional domain: {email!r}"
                )
