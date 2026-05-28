"""Async demo clients that return fixture data without any real I/O.

Each client matches the public async function signatures of the real clients
so :mod:`ado_dashboard.screens.dashboard` can call them transparently.
"""

from __future__ import annotations

from ado_dashboard.demo import fixtures
from ado_dashboard.models import CopilotSession, PullRequest, TriageItem, WorkItem


class DemoAdoClient:
    """Drop-in replacement for :mod:`ado_dashboard.ado_client` in demo mode."""

    async def fetch_my_prs(self) -> list[PullRequest]:
        """Return demo 'My PRs'."""
        return fixtures.get_my_prs()

    async def fetch_reviewing_prs(self) -> list[PullRequest]:
        """Return demo 'Reviewing' PRs."""
        return fixtures.get_reviewing_prs()

    async def fetch_work_items_with_hierarchy(self) -> list[WorkItem]:
        """Return demo work items with parent hierarchy."""
        return fixtures.get_work_items()


class DemoTriageClient:
    """Drop-in replacement for :mod:`ado_dashboard.triage_client` in demo mode."""

    async def fetch_triage_items(
        self, column: str = "Triage", board: str = ""
    ) -> list[TriageItem]:
        """Return demo triage items (ignores column/board filters)."""
        return fixtures.get_triage_items()


class DemoSessionClient:
    """Drop-in replacement for :mod:`ado_dashboard.session_client` in demo mode."""

    async def fetch_sessions(self) -> list[CopilotSession]:
        """Return demo Copilot sessions."""
        return fixtures.get_sessions()
