# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, Textual, httpx, Azure DevOps REST API, PAT auth
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

- Thorin completed contributor docs (2026-05-08): See `docs/ado-integration.md` for Azure DevOps CLI shapes, auth, error handling, and JSON mapping patterns.
- **Thorin OSS Scrub (2026-05-08):** Generified internal identifiers; introduced InvestigationLauncher Protocol adapter. Legacy env var renamed to `WIP_DASHBOARD_REPO_ROOT`. See `.squad/decisions/decisions.md`.
- **Dwalin Test Suite (2026-05-08):** 79 tests written for config, investigation, models, triage. Establishes pytest fixtures, autouse patterns for module state, and test conventions. See `src/tests/` and `.squad/decisions/decisions.md`.
- **Balin az --organization bug (2026-05-27):** After rename to `ado-dashboard`, setup wizard accepted a bare org name (`"microsoft"`) instead of a full URL. This reached `az` as `--org microsoft`, which az rejects (requires full URI). Fix: (1) repaired live config file to `"https://dev.azure.com/microsoft"`; (2) added `_normalize_org_url()` in `config.py` applied in both `load_from_file()` and `apply_overrides()`; (3) added inline normalization in `setup_wizard.py` before the value is saved. Also corrected `ado_project` which contained a multi-value comma-separated string instead of a single project name. Flagged UX copy in wizard banner ("WIP Dashboard") to Bofur for rename.
- **Balin Public-Readiness Audit (2026-05-28):** Full secret scan + internal-identifier audit across 32 commits. No blockers found. Auth model (az CLI delegation, no PAT storage) is sound. Two 🟡 items: (1) `ado_client.py:39` `log.debug("az command: ...")` writes user email/project to debug logs (gitignored, not a git exposure risk, but PII in bug reports); (2) `AgencyLauncher` references Microsoft-internal `agency` CLI (clearly labeled, no credentials, cosmetic). The `aka.ms/agency-cli` link in source is an internal redirect. Dual `wip_dashboard`/`ado_dashboard` copies mean any fix must be applied twice. Full report: `.squad/decisions/inbox/balin-public-audit.md`.
