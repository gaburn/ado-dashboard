"""Detail screen for viewing a single PR, work item, or triage item."""

from __future__ import annotations

import logging
import re
import webbrowser
from typing import Generator

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from wip_dashboard.ado_client import (
    ADOClientError,
    fetch_pr_detail,
    fetch_work_item_detail,
)
from wip_dashboard import config
from wip_dashboard.models import CopilotSession, PullRequest, TriageItem, WorkItem
from wip_dashboard.session_client import resume_session

log = logging.getLogger(__name__)

_DESCRIPTION_WIDGET_ID = "detail-description"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_html(text: str) -> str:
    """Crude HTML-to-plain-text conversion for ADO descriptions."""
    # Replace <br>, <p>, <li> with newlines for readability
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|li|div|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _vote_css_class(vote: int) -> str:
    """Map a reviewer vote code to a CSS class name."""
    if vote >= 10:
        return "reviewer-approved"
    if vote >= 5:
        return "reviewer-approved"
    if vote <= -10:
        return "reviewer-rejected"
    if vote <= -5:
        return "reviewer-waiting"
    return "reviewer-none"


def _vote_text(vote: int) -> str:
    """Human-readable label for a reviewer vote code."""
    return {
        10: "Approved",
        5: "Approved with suggestions",
        0: "No vote",
        -5: "Waiting for author",
        -10: "Rejected",
    }.get(vote, "Unknown")


# ---------------------------------------------------------------------------
# Detail Screen
# ---------------------------------------------------------------------------
class DetailScreen(Screen):
    """Display detailed information for a single PR or Work Item."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", priority=True),
        Binding("o", "open_browser", "Open in browser"),
        Binding("f", "focus_terminal", "Focus Terminal"),
        Binding("R", "resume_session", "Resume Session"),
    ]

    def __init__(self, item: PullRequest | WorkItem | TriageItem | CopilotSession) -> None:
        super().__init__()
        self._item = item

    # -- Layout --------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="detail-screen"):
            if isinstance(self._item, PullRequest):
                yield from self._compose_pr(self._item)
            elif isinstance(self._item, TriageItem):
                yield from self._compose_triage_item(self._item)
            elif isinstance(self._item, CopilotSession):
                yield from self._compose_session(self._item)
            else:
                yield from self._compose_work_item(self._item)
        yield Footer()

    def on_mount(self) -> None:
        """Kick off a background fetch for richer detail (description, reviewers)."""
        self._fetch_detail()

    # -- Async detail fetch --------------------------------------------------

    @work(exclusive=True)
    async def _fetch_detail(self) -> None:
        """Fetch the full detail from ADO and refresh the description widget."""
        # Triage items and sessions already have their full detail.
        if isinstance(self._item, (TriageItem, CopilotSession)):
            return

        try:
            if isinstance(self._item, PullRequest):
                detail = await fetch_pr_detail(self._item.id)
            else:
                detail = await fetch_work_item_detail(self._item.id)
        except ADOClientError as exc:
            log.warning("Detail fetch failed for #%d: %s", self._item.id, exc)
            self.notify(f"Could not load full detail: {exc}", severity="warning", markup=False)
            return
        except Exception as exc:
            log.exception("Unexpected error fetching detail for #%d", self._item.id)
            self.notify(f"Detail fetch error: {exc}", severity="warning", markup=False)
            return

        self._item = detail
        self._refresh_description(detail)

    def _refresh_description(self, item: PullRequest | WorkItem) -> None:
        """Update the description Static widget after fetching detail."""
        try:
            widget = self.query_one(f"#{_DESCRIPTION_WIDGET_ID}", Static)
        except Exception:
            return  # widget not yet mounted

        if item.description:
            widget.update(_strip_html(item.description)[:3000])
        else:
            widget.update("No description provided.")

    # -- PR compose ----------------------------------------------------------

    @staticmethod
    def _compose_pr(pr: PullRequest) -> Generator[Static, None, None]:
        """Yield Static widgets that render pull request detail fields."""
        yield Static("Pull Request Details", classes="section-heading")

        yield Static("ID", classes="field-label")
        yield Static(str(pr.id), classes="field-value")

        yield Static("Title", classes="field-label")
        yield Static(pr.title, classes="field-value")

        yield Static("Status", classes="field-label")
        yield Static(pr.status.capitalize(), classes="field-value")

        yield Static("Author", classes="field-label")
        yield Static(pr.author, classes="field-value")

        yield Static("Repository", classes="field-label")
        yield Static(pr.repo_name, classes="field-value")

        yield Static("Branch", classes="field-label")
        yield Static(f"{pr.short_source} → {pr.short_target}", classes="field-value")

        yield Static("Created", classes="field-label")
        yield Static(
            f"{pr.created_date.strftime('%Y-%m-%d %H:%M UTC')}  ({pr.age} ago)",
            classes="field-value",
        )

        yield Static("Draft", classes="field-label")
        if pr.is_draft:
            yield Static("Yes", classes="field-value draft-indicator")
        else:
            yield Static("No", classes="field-value")

        # -- Reviewers -------------------------------------------------------
        if pr.reviewers:
            yield Static("Reviewers", classes="section-heading")
            for rev in pr.reviewers:
                css_class = _vote_css_class(rev.vote)
                yield Static(
                    f"{rev.vote_emoji}  {rev.name}  —  {_vote_text(rev.vote)}",
                    classes=css_class,
                )

        # -- Labels ----------------------------------------------------------
        if pr.labels:
            yield Static("Labels", classes="section-heading")
            yield Static(", ".join(pr.labels), classes="field-value")

        # -- Description (placeholder until detail fetch completes) ----------
        yield Static("Description", classes="section-heading")
        if pr.description:
            desc_text = _strip_html(pr.description)[:3000]
        else:
            desc_text = "Loading…"
        yield Static(desc_text, id=_DESCRIPTION_WIDGET_ID, classes="field-value")

        # -- URL -------------------------------------------------------------
        yield Static(pr.url, classes="url-link")

    # -- Work Item compose ---------------------------------------------------

    @staticmethod
    def _compose_work_item(wi: WorkItem) -> Generator[Static, None, None]:
        """Yield Static widgets that render work item detail fields."""
        yield Static("Work Item Details", classes="section-heading")

        yield Static("ID", classes="field-label")
        yield Static(str(wi.id), classes="field-value")

        yield Static("Title", classes="field-label")
        yield Static(wi.title, classes="field-value")

        yield Static("Type", classes="field-label")
        yield Static(f"{wi.type_emoji}  {wi.work_item_type}", classes="field-value")

        yield Static("State", classes="field-label")
        yield Static(wi.state, classes="field-value")

        if wi.priority is not None:
            yield Static("Priority", classes="field-label")
            yield Static(str(wi.priority), classes="field-value")

        yield Static("Iteration", classes="field-label")
        yield Static(wi.iteration_path or "—", classes="field-value")

        yield Static("Area Path", classes="field-label")
        yield Static(wi.area_path or "—", classes="field-value")

        # -- Tags ------------------------------------------------------------
        if wi.tags:
            yield Static("Tags", classes="section-heading")
            yield Static(", ".join(wi.tags), classes="field-value")

        # -- Description (placeholder until detail fetch completes) ----------
        yield Static("Description", classes="section-heading")
        if wi.description:
            desc_text = _strip_html(wi.description)[:3000]
        else:
            desc_text = "Loading…"
        yield Static(desc_text, id=_DESCRIPTION_WIDGET_ID, classes="field-value")

        # -- URL -------------------------------------------------------------
        yield Static(wi.url, classes="url-link")

    # -- Triage Item compose -------------------------------------------------

    @staticmethod
    def _compose_triage_item(item: TriageItem) -> Generator[Static, None, None]:
        """Yield Static widgets that render triage item detail fields."""
        yield Static("Triage Item Details", classes="section-heading")

        yield Static("ID", classes="field-label")
        yield Static(str(item.id), classes="field-value")

        yield Static("Title", classes="field-label")
        yield Static(item.title, classes="field-value")

        yield Static("Type", classes="field-label")
        yield Static(
            f"{item.type_emoji}  {item.work_item_type}", classes="field-value"
        )

        yield Static("Priority", classes="field-label")
        yield Static(item.priority_label, classes="field-value")

        yield Static("Assigned To", classes="field-label")
        yield Static(item.assigned_to or "Unassigned", classes="field-value")

        yield Static("Age", classes="field-label")
        yield Static(
            f"{item.age}  (created {item.created_date})", classes="field-value"
        )

        # -- Tags ------------------------------------------------------------
        if item.tags:
            yield Static("Tags", classes="section-heading")
            yield Static(item.tags, classes="field-value")

        # -- Description -----------------------------------------------------
        if item.description:
            yield Static("Description", classes="section-heading")
            yield Static(
                item.description[:3000],
                id=_DESCRIPTION_WIDGET_ID,
                classes="field-value",
            )

        # -- PR link ---------------------------------------------------------
        if item.pr_id:
            yield Static("Linked PR", classes="section-heading")
            pr_url = (
                f"{config.ORG_URL}/{config.PROJECT}/_git/pullrequest/{item.pr_id}"
            )
            yield Static(f"PR #{item.pr_id}  —  {pr_url}", classes="field-value")

        # -- URL -------------------------------------------------------------
        yield Static(item.url, classes="url-link")

    # -- Session compose -----------------------------------------------------

    @staticmethod
    def _compose_session(session: CopilotSession) -> Generator[Static, None, None]:
        """Yield Static widgets that render Copilot session detail fields."""
        yield Static("Copilot Session", classes="section-heading")
        yield Static("Session ID", classes="field-label")
        yield Static(session.id, classes="field-value")
        yield Static("Status", classes="field-label")
        status = f"{'🟢 Active' if session.is_active else '⚪ Inactive'}"
        if session.pid:
            status += f" (PID: {session.pid})"
        yield Static(status, classes="field-value")
        yield Static("Summary", classes="field-label")
        yield Static(session.summary or "Untitled", classes="field-value")
        yield Static("Working Directory", classes="field-label")
        yield Static(session.cwd, classes="field-value")
        if session.git_root:
            yield Static("Git Root", classes="field-label")
            yield Static(session.git_root, classes="field-value")
        yield Static("Branch", classes="field-label")
        yield Static(session.branch or "—", classes="field-value")
        yield Static("Created", classes="field-label")
        yield Static(f"{session.created_at:%Y-%m-%d %H:%M} ({session.age} ago)", classes="field-value")
        yield Static("Last Active", classes="field-label")
        yield Static(f"{session.updated_at:%Y-%m-%d %H:%M} ({session.last_active} ago)", classes="field-value")
        if session.intent:
            yield Static("Current Intent", classes="field-label")
            yield Static(session.intent, classes="field-value")
        yield Static("Copilot Version", classes="field-label")
        yield Static(session.copilot_version or "Unknown", classes="field-value")
        yield Static("Activity", classes="field-label")
        yield Static(f"{session.event_count} events", classes="field-value")
        yield Static("", classes="section-heading")
        yield Static(session.cwd, classes="url-link")

    # -- Actions -------------------------------------------------------------

    def action_go_back(self) -> None:
        """Pop this screen and return to the dashboard."""
        self.app.pop_screen()

    def action_open_browser(self) -> None:
        """Open the item's ADO page in the default browser."""
        webbrowser.open(self._item.url)
        self.notify(f"Opened #{self._item.id} in browser")

    def action_focus_terminal(self) -> None:
        """Switch focus to the terminal running this session."""
        if not isinstance(self._item, CopilotSession):
            return
        if not self._item.is_active or not self._item.pid:
            self.notify("Session is not active", severity="warning")
            return

        from wip_dashboard.window_focus import focus_terminal_by_pid

        self.notify(f"Focusing terminal (PID {self._item.pid})…")
        success, message = focus_terminal_by_pid(self._item.pid)
        if not success:
            self.notify(f"Focus failed: {message}", severity="warning", markup=False)

    def action_resume_session(self) -> None:
        """Resume a stopped Copilot session in a new terminal tab."""
        if not isinstance(self._item, CopilotSession):
            return
        if self._item.is_active:
            self.notify(
                "Session is already active — use 'f' to focus its terminal",
                severity="information",
            )
            return
        ok, msg = resume_session(self._item)
        if ok:
            self.notify(msg, markup=False)
        else:
            self.notify(msg, severity="error", markup=False)
