# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, pyproject.toml, pipx-installable, keyring for secrets
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->
- **Thorin OSS Scrub (2026-05-08):** Removed Microsoft-internal identifiers; introduced InvestigationLauncher Protocol adapter. Env var renamed: `BAND_REPO_ROOT` → `WIP_DASHBOARD_REPO_ROOT`. See `.squad/decisions/decisions.md`.
- **Thorin+Bofur Package Rename (2026-05-25):** Rename execution complete — `wip-dashboard` → `ado-dashboard`. Package name, CLI entry point, pyproject.toml, all imports, docs, config dirs updated. Users should run `pip install -e .` to register new CLI script. See `.squad/decisions/decisions.md` for full scope.
- **Thorin Env Var Rename Loose-Ends (2026-05-26):** Canonical env var `WIP_DASHBOARD_REPO_ROOT` → `ADO_DASHBOARD_REPO_ROOT` with backward-compat deprecation fallback. Updated `config.py`, README, and `docs/configuration.md`. See decisions.md.
