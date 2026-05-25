"""Entry point for `python -m wip_dashboard` and the `wip-dashboard` CLI command."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    """Build and parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="wip-dashboard",
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
        "--user",
        dest="user_email",
        default=None,
        help="User email address for ADO queries",
    )
    return parser.parse_args()


def main() -> None:
    """Launch the WIP Dashboard TUI application."""
    args = _parse_args()

    from wip_dashboard import config
    from wip_dashboard.setup_wizard import (
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
            print("  Run `wip-dashboard --setup` to reconfigure at any time.\n")

    # Load config file into module globals.
    file_data = load_config()
    config.load_from_file(file_data)

    # Apply CLI overrides (highest priority).
    config.apply_overrides(args)

    # File logging for debugging window-focus and session issues.
    log_file = Path(__file__).resolve().parent.parent.parent / "wip-dashboard.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    logging.getLogger("wip_dashboard").setLevel(logging.DEBUG)
    logging.getLogger("wip_dashboard").addHandler(file_handler)

    # Capture Textual framework-level CSS/styling logs for diagnostics.
    logging.getLogger("textual").setLevel(logging.DEBUG)
    logging.getLogger("textual").addHandler(file_handler)

    # Launch TUI.
    from wip_dashboard.app import WipDashboardApp

    WipDashboardApp().run()


if __name__ == "__main__":
    main()
