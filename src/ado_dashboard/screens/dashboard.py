"""Main dashboard screen with tabbed DataTables for PRs, work items, and triage."""

from __future__ import annotations

import asyncio
import logging
import re
import time
import webbrowser
from operator import attrgetter

from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from ado_dashboard import config, triage_cache
from ado_dashboard.ado_client import (
    fetch_my_prs,
    fetch_reviewing_prs,
    fetch_work_items_with_hierarchy,
)
from ado_dashboard.demo.fixtures import DEMO_USER_EMAIL
from ado_dashboard.investigation_prompts import (
    build_ai_triage_prompt,
    build_board_investigation_prompt,
    build_item_investigation_prompt,
)
from ado_dashboard.models import CopilotSession, PullRequest, TriageItem, WorkItem
from ado_dashboard.session_client import fetch_sessions, launch_investigation, resume_session
from ado_dashboard.triage_categorizer import apply_ai_analysis, categorize_triage_items, generate_action_plan
from ado_dashboard.triage_client import fetch_triage_items

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo-mode client helpers
# ---------------------------------------------------------------------------

def _demo_ado() -> DemoAdoClient | None:  # noqa: F821
    """Return a demo ADO client when DEMO_MODE is active, else None."""
    if not config.DEMO_MODE:
        return None
    from ado_dashboard.demo.clients import DemoAdoClient
    return DemoAdoClient()


def _demo_triage() -> DemoTriageClient | None:  # noqa: F821
    """Return a demo triage client when DEMO_MODE is active, else None."""
    if not config.DEMO_MODE:
        return None
    from ado_dashboard.demo.clients import DemoTriageClient
    return DemoTriageClient()


def _demo_session() -> DemoSessionClient | None:  # noqa: F821
    """Return a demo session client when DEMO_MODE is active, else None."""
    if not config.DEMO_MODE:
        return None
    from ado_dashboard.demo.clients import DemoSessionClient
    return DemoSessionClient()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate text with an ellipsis if it exceeds *max_len*."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _strip_board_prefix(title: str) -> str:
    """Remove board-name prefix patterns like '[Board Name] - ' from titles."""
    cleaned = re.sub(r"^-?\s*\[.*?\]\s*-\s*", "", title)
    return cleaned.strip() or title


def _short_iteration(path: str) -> str:
    """Return the last segment of a backslash-delimited iteration path."""
    return path.rsplit("\\", 1)[-1] if path else ""


def _wi_title_target_width(table: DataTable) -> int:
    """Compute the desired width for the Work Items 'Title' column so the
    table fills its available horizontal space.

    Returns 0 if the table is not yet laid out (no width / no columns).
    """
    if not table.columns:
        return 0
    table_w = table.size.width
    if table_w <= 0:
        return 0
    cols = list(table.columns.values())
    if len(cols) < 3:
        return 0
    cell_pad = getattr(table, "cell_padding", 1)
    overhead = 3 + cell_pad * 2 * len(cols)
    other_content = sum(
        max(col.content_width, len(col.label.plain))
        for i, col in enumerate(cols)
        if i != 2
    )
    return max(table_w - overhead - other_content, 20)


def _fit_wi_title_column(table: DataTable, target: int) -> None:
    """Pin the Work Items Title column to *target* width and refresh layout."""
    if target <= 0 or not table.columns:
        return
    cols = list(table.columns.values())
    if len(cols) < 3:
        return
    title_col = cols[2]
    if title_col.width == target and not title_col.auto_width:
        return
    title_col.auto_width = False
    title_col.width = target
    title_col.content_width = target
    table.refresh(layout=True)


def _tree_order_work_items(
    items: list[WorkItem],
) -> list[tuple[int, WorkItem]]:
    """Arrange work items in parent→child tree order.

    Returns a list of ``(depth, work_item)`` tuples.  Items whose parent is
    not in *items* are treated as top-level (depth 0).  The order within each
    level is preserved from the input list, so pre-sorting the input gives
    sorted output within each tree level.
    """
    by_id: dict[int, WorkItem] = {wi.id: wi for wi in items}
    children: dict[int | None, list[WorkItem]] = {}
    for wi in items:
        pid = wi.parent_id if (wi.parent_id and wi.parent_id in by_id) else None
        children.setdefault(pid, []).append(wi)

    result: list[tuple[int, WorkItem]] = []
    visited: set[int] = set()

    def _walk(parent_id: int | None, depth: int) -> None:
        for wi in children.get(parent_id, []):
            if wi.id in visited:
                continue
            visited.add(wi.id)
            result.append((depth, wi))
            _walk(wi.id, depth + 1)

    _walk(None, 0)
    return result


# ---------------------------------------------------------------------------
# Sort configuration
# ---------------------------------------------------------------------------

# Column index → (model attribute, display name) for each table type.
_PR_SORT_KEYS: dict[int, tuple[str, str]] = {
    0: ("id", "ID"),
    1: ("title", "Title"),
    2: ("repo_name", "Repo"),
    3: ("short_source", "Branch"),
    4: ("created_date", "Age"),
    5: ("is_draft", "Draft"),
}

_REVIEWING_SORT_KEYS: dict[int, tuple[str, str]] = {
    0: ("id", "ID"),
    1: ("title", "Title"),
    2: ("repo_name", "Repo"),
    3: ("short_source", "Branch"),
    4: ("created_date", "Age"),
    5: ("is_draft", "Draft"),
    6: ("_my_vote", "Vote"),
}

_WI_SORT_KEYS: dict[int, tuple[str, str]] = {
    0: ("id", "ID"),
    1: ("work_item_type", "Type"),
    2: ("title", "Title"),
    3: ("state", "State"),
    4: ("iteration_path", "Iteration"),
    5: ("changed_date", "Age"),
}

_SESSION_SORT_KEYS: dict[int, tuple[str, str]] = {
    0: ("is_active", "Status"),
    1: ("summary", "Summary"),
    2: ("cwd", "Directory"),
    3: ("branch", "Branch"),
    4: ("updated_at", "Last Active"),
    5: ("intent", "Intent"),
}

# Shift+0 … Shift+6 produce these characters on a US keyboard.
_SORT_KEY_CHARS = ")!@#$%^"

# Priority group display configuration: emoji, label, initially collapsed?
_PRIORITY_DISPLAY: dict[int, tuple[str, str, bool]] = {
    1: ("🔴", "Critical", False),
    2: ("🟠", "High", False),
    3: ("🟡", "Medium", False),
    4: ("⚪", "Low", False),
}


# ---------------------------------------------------------------------------
# Dashboard Screen
# ---------------------------------------------------------------------------
class DashboardScreen(Screen):
    """Five-tab dashboard showing My PRs, Reviewing PRs, Work Items, Triage, and Copilot Sessions."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_browser", "Open in browser"),
        Binding("c", "copy_to_clipboard", "Copy"),
        Binding("1", "switch_tab('my-prs')", "My PRs"),
        Binding("2", "switch_tab('reviewing')", "Reviewing"),
        Binding("3", "switch_tab('work-items')", "Work Items"),
        Binding("4", "switch_tab('triage')", "Triage"),
        Binding("5", "switch_tab('sessions')", "Copilot Sessions"),
        # Sort by column (Shift+0 … Shift+5). A single footer hint is enough.
        Binding(")", "sort_column(0)", "Sort", show=True, key_display="SHIFT+0"),
        Binding("!", "sort_column(1)", show=False),
        Binding("@", "sort_column(2)", show=False),
        Binding("#", "sort_column(3)", show=False),
        Binding("$", "sort_column(4)", show=False),
        Binding("%", "sort_column(5)", show=False),
        Binding("^", "sort_column(6)", show=False),
        Binding("f", "focus_terminal", "Focus Terminal", show=False),
        Binding("R", "resume_session", "Resume Session"),
        Binding("s", "open_settings", "Settings"),
        Binding("/", "search", "Search", show=True),
        Binding("h", "show_help", "Help"),
        Binding("i", "investigate_item", "Investigate"),
        Binding("I", "investigate_board", "Investigate Board", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._my_prs: list[PullRequest] = []
        self._reviewing_prs: list[PullRequest] = []
        self._work_items: list[WorkItem] = []
        self._triage_items: list[TriageItem] = []
        self._sessions: list[CopilotSession] = []
        self._triage_groups: dict[int, list[TriageItem]] = {}
        # Validate selected board is in available options; fall back to first option
        valid_values = {v for _, v in config.TRIAGE_BOARD_OPTIONS}
        if config.TRIAGE_BOARD in valid_values:
            self._selected_board = config.TRIAGE_BOARD
        else:
            self._selected_board = (
                config.TRIAGE_BOARD_OPTIONS[0][1] if config.TRIAGE_BOARD_OPTIONS else ""
            )
        # Per-table sort state: table_id → (column_index, ascending)
        self._sort_state: dict[str, tuple[int, bool]] = {}
        # Generation counter for triage widget IDs (avoids DOM ID conflicts on refresh)
        self._triage_gen: int = 0
        # Generation counter for board changes (guards against stale AI enrich results)
        self._board_gen: int = 0
        self._ai_triage_launch_time: float = 0.0
        self._ai_triage_poll_timer = None
        self._ai_triage_poll_gen: int = 0
        self._wi_title_width: int = 0
        self._ai_triage_status: str = ""
        self._ai_action_plan: str = ""
        # Search/filter state
        self._search_query: str = ""
        self._search_active: bool = False
        self._all_my_prs: list[PullRequest] = []
        self._all_reviewing_prs: list[PullRequest] = []
        self._all_work_items: list[WorkItem] = []
        self._all_sessions: list[CopilotSession] = []

    # -- Layout --------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("My PRs", id="my-prs"):
                yield DataTable(id="pr-table", cursor_type="row", zebra_stripes=True)
            with TabPane("Reviewing", id="reviewing"):
                yield DataTable(
                    id="reviewing-table", cursor_type="row", zebra_stripes=True
                )
            with TabPane("Work Items", id="work-items"):
                yield DataTable(
                    id="work-items-table", cursor_type="row", zebra_stripes=True
                )
            with TabPane("Triage", id="triage"):
                if config.TRIAGE_BOARD_OPTIONS:
                    yield Select(
                        config.TRIAGE_BOARD_OPTIONS,
                        value=self._selected_board,
                        allow_blank=False,
                        id="triage-board-select",
                    )
                yield VerticalScroll(id="triage-scroll")
            with TabPane("Copilot Sessions", id="sessions"):
                yield DataTable(id="sessions-table", cursor_type="row", zebra_stripes=True)
        yield Input(id="search-input", placeholder="Search… (Esc to close)", classes="hidden")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._setup_columns()
        self._load_data()

    def on_resize(self, event: events.Resize) -> None:
        """Re-fit Work Items Title column when terminal width changes."""
        try:
            table = self.query_one("#work-items-table", DataTable)
        except Exception:
            return
        target = _wi_title_target_width(table)
        if target <= 0:
            return
        # Only re-render rows when the change is large enough to matter;
        # always pin the column width so the table fills the viewport.
        if abs(target - self._wi_title_width) > 4 and self._work_items:
            self._wi_title_width = target
            self._work_items = self._populate_wi_table(
                table, self._work_items, title_max=target
            )
        _fit_wi_title_column(table, target)

    # -- Table setup ---------------------------------------------------------

    def _setup_columns(self) -> None:
        """Add column headers to each DataTable (called once)."""
        pr_cols = ("ID", "Title", "Repo", "Branch", "Age", "Draft", "Status")
        self.query_one("#pr-table", DataTable).add_columns(*pr_cols)

        reviewing_cols = ("ID", "Title", "Repo", "Branch", "Age", "Draft", "Vote")
        self.query_one("#reviewing-table", DataTable).add_columns(*reviewing_cols)

        wi_cols = ("ID", "Type", "Title", "State", "Iteration", "Age")
        self.query_one("#work-items-table", DataTable).add_columns(*wi_cols)

        session_cols = ("", "Summary", "Directory", "Branch", "Last Active", "Intent")
        self.query_one("#sessions-table", DataTable).add_columns(*session_cols)

    # -- Data loading --------------------------------------------------------

    @work(exclusive=True)
    async def _load_data(self) -> None:
        """Fetch all data from ADO and populate tabs progressively.

        Stage 1: Fetch and display My PRs immediately so the dashboard
        is usable while remaining tabs continue loading in the background.
        Stage 2: Fetch remaining data sources in parallel, rendering each
        tab as its data arrives.
        """
        pr_table = self.query_one("#pr-table", DataTable)
        reviewing_table = self.query_one("#reviewing-table", DataTable)
        wi_table = self.query_one("#work-items-table", DataTable)
        sessions_table = self.query_one("#sessions-table", DataTable)
        all_tables = [pr_table, reviewing_table, wi_table, sessions_table]

        for table in all_tables:
            table.loading = True

        # Clear search state on data reload
        self._search_query = ""
        try:
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
            if self._search_active:
                search_input.add_class("hidden")
                self._search_active = False
        except Exception:
            pass

        # -- Stage 1: Fetch My PRs first for fast time-to-interactive ------
        _demo_ado_client = _demo_ado()
        try:
            if _demo_ado_client:
                my_prs = await _demo_ado_client.fetch_my_prs()
            else:
                my_prs = await fetch_my_prs()
        except Exception as exc:
            log.exception("My PRs fetch failed")
            self.notify(f"Fetch error: {exc}", severity="error", timeout=10, markup=False)
            my_prs = []

        self._my_prs = my_prs
        self._all_my_prs = list(my_prs)
        self._populate_pr_table(pr_table, my_prs)
        pr_table.loading = False
        if my_prs:
            pr_table.focus()
        self._update_status_bar()

        # -- Stage 2: Fetch remaining data in parallel, render as ready ----
        my_pr_ids = {pr.id for pr in my_prs}
        _demo_email = DEMO_USER_EMAIL if _demo_ado_client else config.USER_EMAIL

        async def _fetch_and_populate_reviewing() -> list[PullRequest]:
            try:
                if _demo_ado_client:
                    prs = await _demo_ado_client.fetch_reviewing_prs()
                else:
                    prs = await fetch_reviewing_prs()
            except Exception as exc:
                log.warning("Reviewing PRs fetch failed: %s", exc)
                self.notify(f"Fetch error: {exc}", severity="error", timeout=10, markup=False)
                prs = []
            prs = [pr for pr in prs if pr.id not in my_pr_ids]
            prs = [pr for pr in prs if not pr.has_declined(_demo_email)]
            self._reviewing_prs = prs
            self._all_reviewing_prs = list(prs)
            self._populate_reviewing_table(reviewing_table, prs, _demo_email)
            reviewing_table.loading = False
            self._update_status_bar()
            return prs

        async def _fetch_and_populate_work_items() -> list[WorkItem]:
            try:
                if _demo_ado_client:
                    items = await _demo_ado_client.fetch_work_items_with_hierarchy()
                else:
                    items = await fetch_work_items_with_hierarchy()
            except Exception as exc:
                log.warning("Work items fetch failed: %s", exc)
                self.notify(f"Fetch error: {exc}", severity="error", timeout=10, markup=False)
                items = []
            self._work_items = self._populate_wi_table(
                wi_table, items, title_max=_wi_title_target_width(wi_table)
            )
            _fit_wi_title_column(wi_table, _wi_title_target_width(wi_table))
            self._all_work_items = list(items)
            wi_table.loading = False
            self._update_status_bar()
            return items

        async def _fetch_and_populate_triage() -> list[TriageItem]:
            scroll = self.query_one("#triage-scroll", VerticalScroll)
            await scroll.remove_children()
            _demo_triage_client = _demo_triage()
            board_name = next(
                (name for name, value in config.TRIAGE_BOARD_OPTIONS if value == self._selected_board),
                self._selected_board or ("Fellowship" if _demo_triage_client else "Triage Board"),
            )
            await scroll.mount(Static(f"Loading {board_name}…", classes="triage-empty"))
            await scroll.mount(LoadingIndicator())

            if _demo_triage_client:
                try:
                    items = await _demo_triage_client.fetch_triage_items()
                except Exception as exc:
                    log.warning("Demo triage fetch failed: %s", exc)
                    items = []
            elif not config.TRIAGE_SCRIPT_PATH:
                log.info("Triage: no script configured, skipping fetch")
                items = []
            else:
                try:
                    items = await fetch_triage_items(board=self._selected_board)
                except Exception as exc:
                    log.warning("Triage fetch failed (non-fatal): %s", exc)
                    self.notify(f"Triage: {exc}", severity="warning", timeout=8, markup=False)
                    items = []
            self._triage_items = items
            self._triage_groups = categorize_triage_items(items)
            self._ai_action_plan = generate_action_plan(self._triage_groups)
            await self._populate_triage_groups()
            if items:
                try:
                    triage_pane = self.query_one("#triage", TabPane)
                    tc = self.query_one(TabbedContent)
                    tab = tc.get_tab(f"tab-{triage_pane.id}")
                    tab.label = f"Triage ({len(items)})"
                except Exception:
                    pass
            self._update_status_bar()
            return items

        async def _fetch_and_populate_sessions() -> list[CopilotSession]:
            _demo_session_client = _demo_session()
            try:
                if _demo_session_client:
                    sess = await _demo_session_client.fetch_sessions()
                else:
                    sess = await fetch_sessions()
            except Exception as exc:
                log.warning("Sessions fetch failed: %s", exc)
                sess = []
            self._sessions = sess
            self._all_sessions = list(sess)
            self._populate_sessions_table(sessions_table, sess)
            sessions_table.loading = False
            self._update_status_bar()
            return sess

        reviewing_prs, work_items, triage_items, sessions = await asyncio.gather(
            _fetch_and_populate_reviewing(),
            _fetch_and_populate_work_items(),
            _fetch_and_populate_triage(),
            _fetch_and_populate_sessions(),
        )

        # If My PRs was empty, focus first non-empty table
        if not my_prs:
            for table in all_tables:
                if table.row_count > 0:
                    table.focus()
                    break

        self._update_status_bar()

        # AI enrichment in background — skip in demo mode
        if triage_items and not config.DEMO_MODE:
            self._start_ai_enrichment()

        total = len(my_prs) + len(reviewing_prs) + len(work_items) + len(triage_items) + len(sessions)
        if total == 0 and not config.DEMO_MODE:
            self.notify("No items found — check your ADO config", severity="warning")
        else:
            log.info(
                "Loaded %d my PRs, %d reviewing, %d work items, %d triage, %d sessions",
                len(my_prs), len(reviewing_prs), len(work_items),
                len(triage_items), len(sessions),
            )

    def _start_ai_enrichment(self) -> None:
        """Route AI enrichment based on config.AI_TRIAGE_MODE."""
        self._ai_triage_status = ""
        mode = config.AI_TRIAGE_MODE.lower()
        if mode == "copilot":
            self._start_copilot_triage()
        # "off" or unknown → no enrichment

    @work(exclusive=True, group="copilot-triage")
    async def _start_copilot_triage(self) -> None:
        """Launch Copilot triage or use cached results."""
        if not self._triage_items:
            return

        gen = self._board_gen

        # Stop any existing poll timer
        if self._ai_triage_poll_timer is not None:
            self._ai_triage_poll_timer.stop()
            self._ai_triage_poll_timer = None

        # Check cache first
        if triage_cache.is_cache_fresh(self._selected_board):
            analysis = triage_cache.read_cached_triage(self._selected_board)
            if analysis is not None and gen == self._board_gen:
                age = triage_cache.cache_age_str(self._selected_board)
                self._triage_groups = apply_ai_analysis(self._triage_items, analysis)
                self._ai_action_plan = analysis.action_plan
                self._ai_triage_status = f"🤖 Analysis: cached ({age} ago)"
                await self._populate_triage_groups()
                self.notify(f"🤖 Using cached AI triage ({age} old)", timeout=3)
                self._update_status_bar()
                return

        # Build prompt and launch Copilot session
        output_path = str(triage_cache.cache_path(self._selected_board))
        prompt = build_ai_triage_prompt(self._selected_board, output_path)

        board_name = next(
            (name for name, value in config.TRIAGE_BOARD_OPTIONS if value == self._selected_board),
            "Triage Board",
        )

        ok, msg = launch_investigation(
            prompt=prompt,
            title=f"AI Triage: {board_name}",
            cwd=config.REPO_ROOT or None,
            model=config.INVESTIGATION_MODEL,
            agent=config.INVESTIGATION_AGENT,
        )

        if not ok:
            log.warning("Copilot triage launch failed: %s", msg)
            self._ai_triage_status = "📋 Analysis: rule-based (Copilot unavailable)"
            return

        self._ai_triage_launch_time = time.time()
        self._ai_triage_poll_gen = gen
        self._ai_triage_status = "🤖 Analysis: waiting for Copilot…"
        self.notify("🤖 AI triage launched in background…", timeout=5)

        # Start polling every 4 seconds
        self._ai_triage_poll_timer = self.set_interval(4, self._poll_copilot_triage)

    async def _poll_copilot_triage(self) -> None:
        """Poll for Copilot triage results (called by timer)."""
        # Guard: board changed
        if self._board_gen != self._ai_triage_poll_gen:
            if self._ai_triage_poll_timer is not None:
                self._ai_triage_poll_timer.stop()
                self._ai_triage_poll_timer = None
            return

        # Guard: timeout (5 minutes)
        if time.time() - self._ai_triage_launch_time > 300:
            if self._ai_triage_poll_timer is not None:
                self._ai_triage_poll_timer.stop()
                self._ai_triage_poll_timer = None
            self._ai_triage_status = "📋 Analysis: rule-based (Copilot timed out)"
            self.notify("AI triage timed out — showing rule-based results", severity="warning", timeout=5)
            return

        # Check if file appeared/updated since launch
        if not triage_cache.is_cache_newer_than(self._selected_board, self._ai_triage_launch_time):
            return  # Not ready yet, timer fires again

        # Results are ready!
        if self._ai_triage_poll_timer is not None:
            self._ai_triage_poll_timer.stop()
            self._ai_triage_poll_timer = None

        analysis = triage_cache.read_cached_triage(self._selected_board)
        if analysis is None:
            return  # Corrupt file, will retry if timer was still running

        if self._board_gen != self._ai_triage_poll_gen:
            return  # Board changed while we were reading

        self._triage_groups = apply_ai_analysis(self._triage_items, analysis)
        self._ai_action_plan = analysis.action_plan
        self._ai_triage_status = "🤖 Analysis: Copilot"
        await self._populate_triage_groups()
        self.notify("🤖 AI triage complete (via Copilot)", timeout=3)
        self._update_status_bar()

    @on(Select.Changed, "#triage-board-select")
    def _on_board_changed(self, event: Select.Changed) -> None:
        """Re-fetch triage items when the user switches boards."""
        if event.value is Select.BLANK:
            return
        if event.value == self._selected_board:
            return
        self._board_gen += 1
        if self._ai_triage_poll_timer is not None:
            self._ai_triage_poll_timer.stop()
            self._ai_triage_poll_timer = None
        self._selected_board = str(event.value)
        config.TRIAGE_BOARD = self._selected_board
        self._persist_board_selection(self._selected_board)
        self._refresh_triage()

    @work(exclusive=True, group="triage-fetch")
    async def _refresh_triage(self) -> None:
        """Re-fetch and display triage items for the currently selected board."""
        scroll = self.query_one("#triage-scroll", VerticalScroll)
        await scroll.remove_children()

        board_name = next(
            (name for name, value in config.TRIAGE_BOARD_OPTIONS if value == self._selected_board),
            self._selected_board,
        )
        await scroll.mount(Static(f"Loading {board_name}…", classes="triage-empty"))
        await scroll.mount(LoadingIndicator())

        _demo_triage_client = _demo_triage()
        if _demo_triage_client:
            try:
                items = await _demo_triage_client.fetch_triage_items()
            except Exception as exc:
                log.warning("Demo triage fetch failed: %s", exc)
                items = []
        elif not config.TRIAGE_SCRIPT_PATH:
            log.info("Triage: no script configured, skipping fetch")
            items = []
        else:
            try:
                items = await fetch_triage_items(board=self._selected_board)
            except Exception as exc:
                log.warning("Triage fetch failed: %s", exc)
                self.notify(f"Triage: {exc}", severity="warning", timeout=8, markup=False)
                items = []
        self._triage_items = items
        self._triage_groups = categorize_triage_items(items)
        self._ai_action_plan = generate_action_plan(self._triage_groups)
        await self._populate_triage_groups()
        # Update tab label with count
        try:
            triage_pane = self.query_one("#triage", TabPane)
            tc = self.query_one(TabbedContent)
            tab = tc.get_tab(f"tab-{triage_pane.id}")
            tab.label = f"Triage ({len(items)})" if items else "Triage"
        except Exception:
            pass
        self._update_status_bar()
        # AI enrichment in background — skip in demo mode
        if items and not config.DEMO_MODE:
            self._start_ai_enrichment()

    @staticmethod
    def _populate_pr_table(table: DataTable, prs: list[PullRequest]) -> None:
        """Clear and repopulate a PR DataTable with approval status."""
        table.clear()
        for pr in prs:
            style = pr.approval_style

            # Determine status indicator.
            if style == "green":
                status_cell = Text(" ✓ ", style="bold green")
            elif style == "red":
                status_cell = Text(" ✗ ", style="bold red")
            elif style == "yellow":
                status_cell = Text(" ~ ", style="bold yellow")
            else:
                status_cell = Text(" · ", style="dim")

            # Use dim style for drafts when there is no approval style.
            if not style and pr.is_draft:
                style = "dim"

            if style:
                table.add_row(
                    Text(str(pr.id), style=style),
                    Text(_truncate(pr.title), style=style),
                    Text(pr.repo_name, style=style),
                    Text(pr.short_source, style=style),
                    Text(pr.age, style=style),
                    Text("DRAFT" if pr.is_draft else "", style=style),
                    status_cell,
                )
            else:
                table.add_row(
                    str(pr.id),
                    _truncate(pr.title),
                    pr.repo_name,
                    pr.short_source,
                    pr.age,
                    "",
                    status_cell,
                )

    @staticmethod
    def _populate_reviewing_table(
        table: DataTable, prs: list[PullRequest], user_email: str = ""
    ) -> None:
        """Clear and repopulate the Reviewing DataTable with vote indicators."""
        table.clear()
        email = user_email or config.USER_EMAIL
        for pr in prs:
            vote = pr.my_vote(email)

            # Determine vote indicator with fixed-width text.
            if vote >= 10:
                vote_cell = Text(" ✓ ", style="bold green")
                style = "green"
            elif vote == 5:
                vote_cell = Text(" ~ ", style="bold yellow")
                style = "yellow"
            elif vote <= -10:
                vote_cell = Text(" ✗ ", style="bold red")
                style = "red"
            else:
                vote_cell = Text(" · ", style="dim")
                style = ""

            # Use dim style for drafts when there is no vote style.
            if not style and pr.is_draft:
                style = "dim"

            if style:
                table.add_row(
                    Text(str(pr.id), style=style),
                    Text(_truncate(pr.title), style=style),
                    Text(pr.repo_name, style=style),
                    Text(pr.short_source, style=style),
                    Text(pr.age, style=style),
                    Text("DRAFT" if pr.is_draft else "", style=style),
                    vote_cell,
                )
            else:
                table.add_row(
                    str(pr.id),
                    _truncate(pr.title),
                    pr.repo_name,
                    pr.short_source,
                    pr.age,
                    "",
                    vote_cell,
                )

    @staticmethod
    def _populate_wi_table(
        table: DataTable, items: list[WorkItem], title_max: int | None = None,
    ) -> list[WorkItem]:
        """Clear and repopulate the Work Items DataTable in tree order.

        Returns the items in display order so the caller can update the
        backing list used for cursor-row → item mapping.

        ``title_max`` caps the title column character width; when ``None``
        the legacy 60-char cap is used (preserves existing tests).
        """
        table.clear()
        tree = _tree_order_work_items(items)
        display_order: list[WorkItem] = []
        effective_title_cap = title_max if title_max and title_max > 10 else 60

        for depth, wi in tree:
            indent = "  " * depth
            arrow = "↳ " if depth > 0 else ""
            max_title = max(effective_title_cap - len(indent) - len(arrow), 10)
            title_str = f"{indent}{arrow}{_truncate(wi.title, max_title)}"

            if wi.is_context_parent:
                # Parent items fetched for context only — dim styling
                table.add_row(
                    Text(str(wi.id), style="dim"),
                    Text(f"{wi.type_emoji} {wi.work_item_type}", style="dim"),
                    Text(title_str, style="dim bold"),
                    Text(wi.state, style="dim"),
                    Text(_short_iteration(wi.iteration_path), style="dim"),
                    Text(wi.age, style="dim"),
                )
            else:
                table.add_row(
                    str(wi.id),
                    f"{wi.type_emoji} {wi.work_item_type}",
                    title_str,
                    wi.state,
                    _short_iteration(wi.iteration_path),
                    wi.age,
                )
            display_order.append(wi)

        return display_order

    @staticmethod
    def _populate_sessions_table(table: DataTable, sessions: list[CopilotSession]) -> None:
        """Clear and repopulate the Sessions DataTable."""
        table.clear()
        for session in sessions:
            style = "bold green" if session.is_active else ""
            status = Text(session.status_emoji)
            if style:
                table.add_row(
                    status,
                    Text(_truncate(session.summary or "Untitled", 45), style=style),
                    Text(session.short_cwd, style=style),
                    Text(session.branch, style=style),
                    Text(session.last_active, style=style),
                    Text(_truncate(session.intent, 35), style=style),
                )
            else:
                table.add_row(
                    status,
                    _truncate(session.summary or "Untitled", 45),
                    session.short_cwd,
                    session.branch,
                    session.last_active,
                    _truncate(session.intent, 35),
                )

    async def _populate_triage_groups(self) -> None:
        """Build priority-grouped Collapsible sections inside #triage-scroll."""
        scroll = self.query_one("#triage-scroll", VerticalScroll)
        await scroll.remove_children()

        self._triage_gen += 1
        gen = self._triage_gen

        if not self._triage_items:
            if not config.TRIAGE_SCRIPT_PATH:
                msg = (
                    "No triage board configured. "
                    "Add one in Settings if you'd like to use Triage."
                )
            else:
                msg = "No items in triage queue 🎉"
            await scroll.mount(Static(msg, classes="triage-empty"))
            return

        # Show which analysis mode produced the triage results
        if self._ai_triage_status:
            status_label = self._ai_triage_status
        else:
            status_label = "📋 Analysis: rule-based (configure AI in Settings)"
        await scroll.mount(Static(status_label, classes="ai-status"))

        widgets: list[Collapsible] = []
        for priority in (1, 2, 3, 4):
            items = self._triage_groups.get(priority)
            if not items:
                continue

            emoji, label, collapsed = _PRIORITY_DISPLAY[priority]
            title = f"{emoji} P{priority} — {label} ({len(items)} items)"

            table = DataTable(
                id=f"triage-p{priority}-{gen}",
                cursor_type="row",
                zebra_stripes=True,
            )

            section = Collapsible(
                table,
                title=title,
                collapsed=collapsed,
                classes=f"triage-p{priority}",
            )
            widgets.append(section)

        await scroll.mount_all(widgets)

        # Add columns and rows after mounting (DataTable needs to be in DOM)
        for priority in (1, 2, 3, 4):
            items = self._triage_groups.get(priority)
            if not items:
                continue

            table = self.query_one(f"#triage-p{priority}-{gen}", DataTable)
            why_header = "Why 🤖" if any(item.ai_why for item in items) else "Why"
            table.add_columns("#", "Item", "Category", "Age", why_header)
            for idx, item in enumerate(items, start=1):
                # Build the Item cell with a clickable link on the ID portion
                item_label = f"#{item.id} — {_truncate(_strip_board_prefix(item.title), 45)}"
                item_text = Text(item_label)
                item_text.stylize(f"link {item.url}", 0, len(f"#{item.id}"))

                # Build the Why cell with clickable PR references
                why_str = item.why
                why_text = Text(why_str)
                if config.TRIAGE_PR_REPO:
                    for pr_match in re.finditer(r"PR #(\d+)", why_str):
                        pr_id = pr_match.group(1)
                        pr_url = f"{config.ORG_URL}/{config.PROJECT}/_git/{config.TRIAGE_PR_REPO}/pullrequest/{pr_id}"
                        why_text.stylize(f"link {pr_url}", pr_match.start(), pr_match.end())

                table.add_row(
                    str(idx),
                    item_text,
                    f"{item.category_emoji} {item.category}",
                    item.age,
                    why_text,
                )
            table.styles.height = len(items) + 2

        # Only show cursor on the first triage table
        first_focused = False
        for priority in (1, 2, 3, 4):
            table_id = f"#triage-p{priority}-{gen}"
            try:
                table = self.query_one(table_id, DataTable)
                if not first_focused and table.row_count > 0:
                    table.show_cursor = True
                    first_focused = True
                else:
                    table.show_cursor = False
            except Exception:
                pass

        if self._ai_action_plan:
            plan_str = f"📋 Recommended Action Plan\n\n{self._ai_action_plan}"
            plan_text = Text(plan_str)
            # Linkify #<id> work item references (5+ digit IDs)
            for wi_match in re.finditer(r"#(\d{5,})", plan_text.plain):
                wi_id = int(wi_match.group(1))
                plan_text.stylize(
                    f"link {config.work_item_url(wi_id)}",
                    wi_match.start(),
                    wi_match.end(),
                )
            # Linkify PR #<id> and PR !<id> references (only when triage_pr_repo is configured)
            if config.TRIAGE_PR_REPO:
                for pr_match in re.finditer(r"PR [#!](\d+)", plan_text.plain):
                    pr_id = pr_match.group(1)
                    plan_text.stylize(
                        f"link {config.ORG_URL}/{config.PROJECT}/_git/{config.TRIAGE_PR_REPO}/pullrequest/{pr_id}",
                        pr_match.start(),
                        pr_match.end(),
                    )
            plan_widget = Static(
                plan_text,
                id=f"action-plan-{gen}",
                classes="action-plan",
            )
            await scroll.mount(plan_widget)

    def _update_status_bar(self) -> None:
        """Update the global status bar with item counts."""
        parts = []

        # Demo mode banner — always first so it's visible in screenshots.
        if config.DEMO_MODE:
            parts.append("🎭 DEMO MODE — Fictional data")

        if self._my_prs:
            parts.append(f"My PRs: {len(self._my_prs)}")
        if self._reviewing_prs:
            parts.append(f"Reviewing: {len(self._reviewing_prs)}")
        if self._work_items:
            parts.append(f"Work Items: {len(self._work_items)}")

        # Triage priority breakdown
        if self._triage_items:
            triage_parts = []
            for p in (1, 2, 3, 4):
                emoji = _PRIORITY_DISPLAY[p][0]
                n = len(self._triage_groups.get(p, []))
                if n > 0:
                    triage_parts.append(f"{emoji} {n}")
            parts.append("Triage: " + " ".join(triage_parts))

        if self._sessions:
            active = sum(1 for s in self._sessions if s.is_active)
            parts.append(f"⚡ Copilot Sessions: {active} active / {len(self._sessions)}")

        try:
            bar = self.query_one("#status-bar", Static)
            status_text = "  │  ".join(parts) if parts else ""
            if self._search_query:
                status_text += f'  │  Filter: "{self._search_query}"'
            bar.update(status_text)
        except Exception:
            pass

    # -- Actions-------------------------------------------------------------

    def action_refresh(self) -> None:
        """Re-fetch all data from ADO."""
        triage_cache.invalidate_cache(self._selected_board)
        self._ai_triage_status = ""
        self.notify("Refreshing…")
        self._load_data()

    def action_open_browser(self) -> None:
        """Open the currently highlighted item in the default browser."""
        item = self._get_selected_item()
        if item is None:
            self.notify("No item selected", severity="warning")
            return
        webbrowser.open(item.url)
        self.notify(f"Opened #{item.id} in browser")

    def action_copy_to_clipboard(self) -> None:
        """Copy the currently highlighted item's details to the clipboard."""
        item = self._get_selected_item()
        if item is None:
            self.notify("No item selected", severity="warning")
            return
        self.app.copy_to_clipboard(item.copy_text)
        self.notify("📋 Copied to clipboard", timeout=3)

    def action_focus_terminal(self) -> None:
        """Switch focus to the terminal running the selected Copilot session."""
        item = self._get_selected_item()
        if not isinstance(item, CopilotSession):
            self.notify("Select an active session to focus its terminal", severity="warning")
            return
        if not item.is_active or not item.pid:
            self.notify("Session is not active", severity="warning")
            return

        from ado_dashboard.window_focus import focus_terminal_by_pid

        self.notify(f"Focusing PID {item.pid} for session {item.id[:8]}…")
        success, message = focus_terminal_by_pid(item.pid)
        if not success:
            self.notify(f"Focus failed: {message}", severity="warning", markup=False)

    def action_resume_session(self) -> None:
        """Resume a stopped Copilot session in a new terminal tab."""
        active = self.query_one(TabbedContent).active
        if active != "sessions":
            return
        item = self._get_selected_item()
        if not isinstance(item, CopilotSession):
            self.notify("Select a session to resume", severity="warning")
            return
        if item.is_active:
            self.notify(
                "Session is already active — use 'f' to focus its terminal",
                severity="information",
            )
            return
        ok, msg = resume_session(item)
        if ok:
            self.notify(msg, markup=False)
        else:
            self.notify(msg, severity="error", markup=False)

    def action_show_help(self) -> None:
        """Show keyboard shortcut help."""
        self.notify(
            "↑↓ Navigate  Enter Details  Esc Back\n"
            "1-5 Switch tabs  o Open  c Copy\n"
            "r Refresh  Shift+0…6 Sort column\n"
            "/  Search  s Settings  f Focus Terminal\n"
            "i  Investigate item  I  Investigate Board\n"
            "R  Resume Session  h Help  q Quit",
            title="Keyboard Shortcuts",
            timeout=10,
        )

    def action_investigate_item(self) -> None:
        """Launch a Copilot investigation for the selected triage item."""
        active = self.query_one(TabbedContent).active
        if active != "triage":
            self.notify("Switch to the Triage tab to investigate items", severity="warning")
            return
        item = self._get_selected_item()
        if item is None or not isinstance(item, TriageItem):
            self.notify("Select a triage item to investigate", severity="warning")
            return
        prompt = build_item_investigation_prompt(
            item_id=item.id,
            title=item.title,
            board_url=self._selected_board,
            category=item.category,
            priority_label=item.priority_label,
        )
        ok, msg = launch_investigation(
            prompt=prompt,
            title=f"Investigate #{item.id}",
            cwd=config.REPO_ROOT or None,
            model=config.INVESTIGATION_MODEL,
            agent=config.INVESTIGATION_AGENT,
        )
        if ok:
            self.notify(f"🔍 Launched investigation for #{item.id}", timeout=5)
        else:
            self.notify(f"Failed: {msg}", severity="error", markup=False)

    def action_investigate_board(self) -> None:
        """Launch a Copilot investigation for the entire selected board."""
        active = self.query_one(TabbedContent).active
        if active != "triage":
            self.notify("Switch to the Triage tab first", severity="warning")
            return
        board_name = next(
            (name for name, value in config.TRIAGE_BOARD_OPTIONS if value == self._selected_board),
            "Triage Board",
        )
        prompt = build_board_investigation_prompt(
            board_url=self._selected_board,
            board_display_name=board_name,
        )
        ok, msg = launch_investigation(
            prompt=prompt,
            title=f"Triage {board_name}",
            cwd=config.REPO_ROOT or None,
            model=config.INVESTIGATION_MODEL,
            agent=config.INVESTIGATION_AGENT,
        )
        if ok:
            self.notify(f"🔍 Launched board investigation for {board_name}", timeout=5)
        else:
            self.notify(f"Failed: {msg}", severity="error", markup=False)

    def action_search(self) -> None:
        """Show the search input and focus it."""
        active = self.query_one(TabbedContent).active
        if active == "triage":
            self.notify("Search not available for Triage tab", severity="warning")
            return
        search_input = self.query_one("#search-input", Input)
        search_input.remove_class("hidden")
        self._search_active = True
        search_input.value = self._search_query
        search_input.focus()

    def _dismiss_search(self) -> None:
        """Hide the search input and return focus to the active table."""
        search_input = self.query_one("#search-input", Input)
        search_input.add_class("hidden")
        self._search_active = False
        # Focus the active tab's DataTable
        active = self.query_one(TabbedContent).active
        table_map: dict[str, str] = {
            "my-prs": "#pr-table",
            "reviewing": "#reviewing-table",
            "work-items": "#work-items-table",
            "sessions": "#sessions-table",
        }
        table_selector = table_map.get(active)
        if table_selector:
            try:
                self.query_one(table_selector, DataTable).focus()
            except Exception:
                pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter the active table as the user types in the search input."""
        if event.input.id != "search-input":
            return
        self._search_query = event.value.strip()
        self._apply_search_filter()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Dismiss the search input on Enter, keeping the filter applied."""
        if event.input.id != "search-input":
            return
        self._dismiss_search()

    def _apply_search_filter(self) -> None:
        """Filter the active tab's data and repopulate its table."""
        active = self.query_one(TabbedContent).active

        if active == "triage":
            return

        # Map tab → (all_items, table selector, populate fn, searchable-text extractor)
        def _pr_search_text(pr: PullRequest) -> str:
            return f"{pr.id} {pr.title} {pr.repo_name} {pr.short_source} {pr.age}"

        def _wi_search_text(wi: WorkItem) -> str:
            return f"{wi.id} {wi.work_item_type} {wi.title} {wi.state} {wi.iteration_path} {wi.age}"

        def _session_search_text(s: CopilotSession) -> str:
            return f"{s.summary or ''} {s.short_cwd} {s.branch} {s.last_active} {s.intent}"

        tab_config: dict[str, tuple[list, str, str, object]] = {
            "my-prs": (self._all_my_prs, "#pr-table", "pr", _pr_search_text),
            "reviewing": (self._all_reviewing_prs, "#reviewing-table", "reviewing", _pr_search_text),
            "work-items": (self._all_work_items, "#work-items-table", "wi", _wi_search_text),
            "sessions": (self._all_sessions, "#sessions-table", "session", _session_search_text),
        }
        entry = tab_config.get(active)
        if entry is None:
            return

        all_items, table_selector, table_type, search_text_fn = entry

        # Filter items or use full list when query is empty.
        if self._search_query:
            query = self._search_query.lower()
            filtered = [item for item in all_items if query in search_text_fn(item).lower()]
        else:
            filtered = list(all_items)

        # Repopulate the table with filtered data.
        table = self.query_one(table_selector, DataTable)
        if table_type == "pr":
            self._populate_pr_table(table, filtered)
            self._my_prs = filtered
        elif table_type == "reviewing":
            self._populate_reviewing_table(table, filtered)
            self._reviewing_prs = filtered
        elif table_type == "wi":
            self._work_items = self._populate_wi_table(
                table, filtered, title_max=_wi_title_target_width(table)
            )
            _fit_wi_title_column(table, _wi_title_target_width(table))
        elif table_type == "session":
            self._populate_sessions_table(table, filtered)
            self._sessions = filtered

        self._update_status_bar()

    def action_open_settings(self) -> None:
        """Open the settings screen."""
        from ado_dashboard.screens.settings import SettingsScreen

        def _on_result(changed: bool | None) -> None:
            if changed:
                self.notify("Settings saved — refreshing…")
                self._load_data()

        self.app.push_screen(SettingsScreen(), _on_result)

    def action_switch_tab(self, tab_id: str) -> None:
        """Programmatically switch to the tab with the given id."""
        self.query_one(TabbedContent).active = tab_id

    def action_sort_column(self, col: int) -> None:
        """Sort the active table by *col* index, toggling asc/desc on repeat."""
        active = self.query_one(TabbedContent).active

        if active == "triage":
            self.notify("Triage items are sorted by urgency")
            return

        # Map active tab → (table CSS id, data list, sort-key lookup, populate fn)
        tab_config: dict[str, tuple[str, str]] = {
            "my-prs": ("#pr-table", "pr"),
            "reviewing": ("#reviewing-table", "reviewing"),
            "work-items": ("#work-items-table", "wi"),
            "sessions": ("#sessions-table", "session"),
        }
        entry = tab_config.get(active)
        if entry is None:
            return

        table_selector, table_type = entry
        sort_keys_map = {
            "pr": _PR_SORT_KEYS,
            "reviewing": _REVIEWING_SORT_KEYS,
            "wi": _WI_SORT_KEYS,
            "session": _SESSION_SORT_KEYS,
        }
        sort_keys = sort_keys_map[table_type]

        if col not in sort_keys:
            return

        attr, col_name = sort_keys[col]

        # Resolve the unfiltered data list for this table.
        all_items_map: dict[str, list] = {
            "#pr-table": self._all_my_prs,
            "#reviewing-table": self._all_reviewing_prs,
            "#work-items-table": self._all_work_items,
            "#sessions-table": self._all_sessions,
        }
        all_items = all_items_map[table_selector]
        if not all_items:
            self.notify("Nothing to sort", severity="warning")
            return

        # Toggle ascending/descending when the same column is pressed again.
        table_id = table_selector.lstrip("#")
        prev_col, prev_asc = self._sort_state.get(table_id, (None, True))
        ascending = not prev_asc if prev_col == col else True
        self._sort_state[table_id] = (col, ascending)

        # Sort the unfiltered data list in place.
        if attr == "_my_vote":
            # Vote requires a dynamic lookup, not a simple attribute.
            all_items.sort(
                key=lambda pr: pr.my_vote(config.USER_EMAIL),
                reverse=not ascending,
            )
        else:
            all_items.sort(key=attrgetter(attr), reverse=not ascending)

        # Re-filter and repopulate from the sorted unfiltered list.
        self._apply_search_filter()

        table = self.query_one(table_selector, DataTable)
        table.focus()

        arrow = "↑" if ascending else "↓"
        self.notify(f"Sorted by {col_name} {arrow}")

    # -- Events --------------------------------------------------------------

    def on_key(self, event: events.Key) -> None:
        """Handle Escape for search dismissal and triage arrow-key navigation."""
        # Escape dismisses the search bar and restores all rows
        if event.key == "escape" and self._search_active:
            self._search_query = ""
            self._dismiss_search()
            self._apply_search_filter()
            event.prevent_default()
            event.stop()
            return

        # Only intercept on the triage tab
        if self.query_one(TabbedContent).active != "triage":
            return

        # Only handle up/down arrows
        if event.key not in ("down", "up"):
            return

        # Find the currently focused DataTable
        focused = self.focused
        if not isinstance(focused, DataTable):
            return
        if not focused.id or "triage-p" not in focused.id:
            return

        # Get all triage tables in DOM order
        try:
            scroll = self.query_one("#triage-scroll", VerticalScroll)
            triage_tables = [t for t in scroll.query(DataTable) if t.row_count > 0]
        except Exception:
            return

        if not triage_tables:
            return

        current_idx = None
        for i, t in enumerate(triage_tables):
            if t is focused:
                current_idx = i
                break
        if current_idx is None:
            return

        if event.key == "down" and focused.cursor_row >= focused.row_count - 1:
            # At last row — move to next table
            next_idx = current_idx + 1
            if next_idx < len(triage_tables):
                next_table = triage_tables[next_idx]
                next_table.show_cursor = True
                next_table.focus()
                next_table.move_cursor(row=0)
                focused.show_cursor = False
                event.prevent_default()
                event.stop()

        elif event.key == "up" and focused.cursor_row <= 0:
            # At first row — move to previous table
            prev_idx = current_idx - 1
            if prev_idx >= 0:
                prev_table = triage_tables[prev_idx]
                prev_table.show_cursor = True
                prev_table.focus()
                prev_table.move_cursor(row=prev_table.row_count - 1)
                focused.show_cursor = False
                event.prevent_default()
                event.stop()

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Focus the DataTable inside the newly activated tab."""
        # Always dismiss search and clear filter when switching tabs,
        # even if search was dismissed via Enter (which leaves _search_query set).
        self._search_query = ""
        self._dismiss_search()
        self._apply_search_filter()

        if event.pane.id == "triage":
            # Find the first DataTable with rows inside the triage scroll
            try:
                scroll = event.pane.query_one("#triage-scroll", VerticalScroll)
                for table in scroll.query(DataTable):
                    if table.row_count > 0:
                        table.focus()
                        return
            except Exception:
                pass
            return

        try:
            table = event.pane.query_one(DataTable)
            if table.row_count > 0:
                table.focus()
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Push the detail screen when the user presses Enter on a row."""
        item = self._item_for_table(event.data_table, event.cursor_row)
        if item is None:
            return
        from ado_dashboard.screens.detail import DetailScreen

        self.app.push_screen(DetailScreen(item))

    def on_data_table_focus(self, event: DataTable.Focus) -> None:
        """Show cursor when a DataTable receives focus."""
        event.data_table.show_cursor = True

    def on_data_table_blur(self, event: DataTable.Blur) -> None:
        """Hide cursor when a triage DataTable loses focus."""
        if event.data_table.id and "triage-p" in event.data_table.id:
            event.data_table.show_cursor = False

    # -- Helpers -------------------------------------------------------------

    def _get_selected_item(self) -> PullRequest | WorkItem | TriageItem | CopilotSession | None:
        """Return the item under the cursor in the currently active tab."""
        active = self.query_one(TabbedContent).active

        if active == "triage":
            return self._get_selected_triage_item()

        table_map: dict[
            str,
            tuple[str, list[PullRequest] | list[WorkItem] | list[TriageItem] | list[CopilotSession]],
        ] = {
            "my-prs": ("#pr-table", self._my_prs),
            "reviewing": ("#reviewing-table", self._reviewing_prs),
            "work-items": ("#work-items-table", self._work_items),
            "sessions": ("#sessions-table", self._sessions),
        }
        entry = table_map.get(active)
        if entry is None:
            return None

        table_id, items = entry
        if not items:
            return None

        table = self.query_one(table_id, DataTable)
        row = table.cursor_row
        if 0 <= row < len(items):
            return items[row]
        return None

    def _get_selected_triage_item(self) -> TriageItem | None:
        """Return the triage item under the cursor in the grouped view."""
        try:
            scroll = self.query_one("#triage-scroll", VerticalScroll)
        except Exception:
            return None

        for table in scroll.query(DataTable):
            if not table.has_focus:
                continue
            tid = table.id or ""
            if not tid.startswith("triage-p"):
                continue
            try:
                priority = int(tid.split("-")[1].removeprefix("p"))
            except (ValueError, IndexError):
                continue
            items = self._triage_groups.get(priority)
            if items is None:
                continue
            row = table.cursor_row
            if 0 <= row < len(items):
                return items[row]
        return None

    def _persist_board_selection(self, board: str) -> None:
        """Save the board choice to the config file."""
        from ado_dashboard.setup_wizard import load_config, save_config
        data = load_config()
        data["triage_board"] = board
        save_config(data)

    @staticmethod
    def _item_for_table(
        table: DataTable, cursor_row: int
    ) -> PullRequest | WorkItem | TriageItem | None:
        """Resolve a DataTable + row coordinate to a stored data item.

        This is used by the RowSelected handler where we already have the
        DataTable reference and need to find the corresponding item.  We
        reach back to the screen's item lists via the table's id.
        """
        screen: DashboardScreen = table.screen  # type: ignore[assignment]
        tid = table.id or ""

        # Handle triage priority group tables (triage-p1-{gen}, triage-p2-{gen}, etc.)
        if tid.startswith("triage-p"):
            try:
                priority = int(tid.split("-")[1].removeprefix("p"))
            except (ValueError, IndexError):
                return None
            items = screen._triage_groups.get(priority)
            if items is None:
                return None
            if 0 <= cursor_row < len(items):
                return items[cursor_row]
            return None

        items_by_id: dict[
            str | None,
            list[PullRequest] | list[WorkItem] | list[TriageItem] | list[CopilotSession],
        ] = {
            "pr-table": screen._my_prs,
            "reviewing-table": screen._reviewing_prs,
            "work-items-table": screen._work_items,
            "sessions-table": screen._sessions,
        }
        items = items_by_id.get(table.id)
        if items is None:
            return None
        if 0 <= cursor_row < len(items):
            return items[cursor_row]
        return None
