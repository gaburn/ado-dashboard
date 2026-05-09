# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, Textual, httpx, Azure DevOps REST API, PAT auth
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

- Thorin completed contributor docs (2026-05-08): See `docs/ado-integration.md` for Azure DevOps CLI shapes, auth, error handling, and JSON mapping patterns.
- **Thorin OSS Scrub (2026-05-08):** Removed Microsoft-internal identifiers; introduced InvestigationLauncher Protocol adapter. Env var renamed: `BAND_REPO_ROOT` → `WIP_DASHBOARD_REPO_ROOT`. See `.squad/decisions/decisions.md`.
- **Dwalin Test Suite (2026-05-08):** 79 tests written for config, investigation, models, triage. Establishes pytest fixtures, autouse patterns for module state, and test conventions. See `src/tests/` and `.squad/decisions/decisions.md`.
