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
- **Balin az --organization bug (2026-05-27):** After rename to `ado-dashboard`, setup wizard accepted a bare org name (`"microsoft"`) instead of a full URL. This reached `az` as `--org microsoft`, which az rejects (requires full URI). Fix: (1) repaired live config file to `"https://dev.azure.com/microsoft"`; (2) added `_normalize_org_url()` in `config.py` applied in both `load_from_file()` and `apply_overrides()`; (3) added inline normalization in `setup_wizard.py` before the value is saved. Also corrected `ado_project` which contained a multi-value comma-separated string instead of a single project name. Flagged UX copy in wizard banner ("WIP Dashboard") to Bofur for rename.
