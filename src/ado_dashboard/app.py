"""Textual App class for the ADO Dashboard."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding
from textual.theme import Theme

from ado_dashboard import __build__, __version__
from ado_dashboard.screens.dashboard import DashboardScreen

# Custom theme extending textual-dark with high-contrast colors.
_wip_dark_theme = Theme(
    name="wip-dark",
    primary="#0078d4",
    secondary="#004578",
    accent="#0078d4",
    foreground="#ffffff",
    background="#1e1e1e",
    surface="#252526",
    warning="#ffa62b",
    error="#ba3c5b",
    success="#4EBF71",
    dark=True,
)


class WipDashboardApp(App):
    """Interactive terminal dashboard for Azure DevOps PRs and work items."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "ADO Dashboard"
    SUB_TITLE = f"ADO PRs, Work Items, On-Call Triage, Copilot Sessions — v{__version__} ({__build__})"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Register a high-contrast theme and push the dashboard."""
        self.register_theme(_wip_dark_theme)
        self.theme = "wip-dark"
        self.push_screen(DashboardScreen())
