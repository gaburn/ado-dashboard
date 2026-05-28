# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, Textual, terminal UX, keyboard-first interaction model
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

- Thorin completed contributor docs (2026-05-08): See `docs/configuration.md` for configuration layer resolution, schema, setup wizard, and in-app settings. See `docs/development.md` for UX conventions, CSS patterns, and known cruft tracker.
- **Dwalin Test Suite (2026-05-08):** 79 tests written for config, investigation, models, triage. Establishes pytest fixtures, autouse patterns for module state, and test conventions. See `src/tests/` and `.squad/decisions/decisions.md`.
- **App Rename (2026-07-17):** Updated all user-facing copy in `README.md`, `CONTRIBUTING.md`, and all `docs/*.md` from `wip-dashboard` / `WIP Dashboard` / `wip_dashboard` to `ado-dashboard` / `ADO Dashboard` / `ado_dashboard`. GitHub repo URLs and `cd wip-dashboard` directory references left pending repo rename (Thorin/user coordination). `WIP_DASHBOARD_REPO_ROOT` env var intentionally left as-is — name is determined by code (Thorin's scope).
- **Bofur Triage Empty-State + Notification Fix (2026-05-28):** Two UX problems when `triage_script_path` is unconfigured. (1) Suppressed the noisy `"Triage: triage_script_path is not configured"` toast that fired on app launch — when triage is optional and the user hasn't opted in, the notification is noise. Both `_fetch_and_populate_triage()` and `_refresh_triage()` in `dashboard.py` now short-circuit silently (INFO log only) when `config.TRIAGE_SCRIPT_PATH` is falsy; the notify path is preserved for real errors when a path IS set. (2) Branched the Triage tab empty state in `_populate_triage_groups()`: unconfigured → calm "No triage board configured. Add one in Settings if you'd like to use Triage." (no 🎉); configured-but-empty → keeps original celebratory "No items in triage queue 🎉". (3) Added a docs hint ("See docs/triage-and-investigation.md for setup instructions.") to the Triage Boards section of `settings.py` so anyone actively configuring triage finds the reference there. `s` key binding for Settings is already in the global footer — no new binding needed. See `.squad/decisions/inbox/bofur-triage-empty-state.md`.
- **Bofur UI Copy Audit (2026-07-17):** Fixed stale user-visible copy throughout `src/ado_dashboard/`:
  - `setup_wizard.py`: Banner "WIP Dashboard — First-Run Setup" → "ADO Dashboard — First-Run Setup"
  - `app.py`: Docstring "WIP Dashboard" → "ADO Dashboard" and `TITLE = "WIP Dashboard"` → `TITLE = "ADO Dashboard"`
  - `__main__.py`: Main function docstring "WIP Dashboard" → "ADO Dashboard"
  - `__init__.py`: Module docstring "WIP Dashboard" → "ADO Dashboard"
  - `screens/__init__.py`: Module docstring "WIP Dashboard" → "ADO Dashboard"
  - Intentionally left unchanged: class names (`WipDashboardApp`, `_wip_dark_theme`), theme identifier `"wip-dark"`, log file name `ado-dashboard.log`, config dir `ado-dashboard` (all stable identifiers per Thorin/Balin). Syntax validated via `py_compile`.
- **Bofur Sessions Tab Rename (2026-07-17):** Renamed "Sessions" tab to "Copilot Sessions" in all user-facing labels and documentation. Updated 7 strings across 4 files: (1) `dashboard.py`: TabPane label, keyboard binding label, docstring, and status bar text; (2) `app.py`: subtitle; (3) `README.md`: tab table header and features description; (4) `architecture.md`: process documentation. Left internal identifiers unchanged: `sessions_tab`, `_sessions`, `session_client.py`, CSS `/* Sessions table */` comment. Python compile check passed.
