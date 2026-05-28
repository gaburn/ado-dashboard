"""Entry point for `python -m ado_dashboard` and the `ado-dashboard` CLI command."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import platformdirs


def _parse_args() -> argparse.Namespace:
    """Build and parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="ado-dashboard",
        description="Interactive terminal dashboard for Azure DevOps PRs and work items.",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive setup wizard",
    )
    parser.add_argument(
        "--org",
        dest="org_url",
        default=None,
        help="Azure DevOps organization URL (e.g. https://dev.azure.com/myorg)",
    )
    parser.add_argument(
        "--project",
        dest="project",
        default=None,
        help="Azure DevOps project name",
    )
    parser.add_argument(
        "--projects",
        dest="projects",
        default=None,
        help="Comma-separated list of ADO projects for PR queries",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help=(
            "Run in demo mode with fictional fixture data — no Azure DevOps "
            "setup or authentication required. Great for screenshots."
        ),
    )
    parser.add_argument(
        "--user",
        dest="user_email",
        default=None,
        help="User email address for ADO queries",
    )
    return parser.parse_args()


def main() -> None:
    """Launch the ADO Dashboard TUI application."""
    args = _parse_args()

    from ado_dashboard import config

    # Activate demo mode if --demo flag or ADO_DASHBOARD_DEMO env var is set.
    if getattr(args, "demo", False):
        config.DEMO_MODE = True

    if config.DEMO_MODE:
        # Demo mode: skip setup wizard and config loading entirely.
        log_dir = Path(platformdirs.user_log_path("ado-dashboard"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "ado-dashboard.log"
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
        logging.getLogger("ado_dashboard").setLevel(logging.DEBUG)
        logging.getLogger("ado_dashboard").addHandler(file_handler)
        from ado_dashboard.app import WipDashboardApp
        WipDashboardApp().run()
        return

    from ado_dashboard.setup_wizard import (
        config_file_exists,
        load_config,
        run_setup,
        save_config,
    )

    # Run setup wizard if requested or if no config file exists yet.
    if args.setup or not config_file_exists():
        existing = load_config()
        config_data = run_setup(existing_config=existing if existing else None)
        if config_data:
            saved_path = save_config(config_data)
            print(f"\n✓ Configuration saved to {saved_path}")
            print("  Run `ado-dashboard --setup` to reconfigure at any time.\n")

    # Load config file into module globals.
    file_data = load_config()
    config.load_from_file(file_data)

    # Apply CLI overrides (highest priority).
    config.apply_overrides(args)

    # File logging for debugging window-focus and session issues.
    log_dir = Path(platformdirs.user_log_path("ado-dashboard"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ado-dashboard.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    logging.getLogger("ado_dashboard").setLevel(logging.DEBUG)
    logging.getLogger("ado_dashboard").addHandler(file_handler)

    # Capture Textual framework-level CSS/styling logs for diagnostics.
    logging.getLogger("textual").setLevel(logging.DEBUG)
    logging.getLogger("textual").addHandler(file_handler)

    # Launch TUI.
    from ado_dashboard.app import WipDashboardApp

    WipDashboardApp().run()


if __name__ == "__main__":
    main()
