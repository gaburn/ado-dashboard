# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, pyproject.toml, pipx-installable, keyring for secrets
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

- **Glóin PyPI Prep Execution (2026-07-17):** Closed all 8 packaging blockers for v0.2.1. `pyproject.toml` now has full PEP 621 metadata (readme, license, authors, keywords, classifiers, [project.urls]). `platformdirs>=3.0` added as explicit runtime dep; `textual` bounded to `<5`. Log file path in `__main__.py` moved from `__file__` parent (site-packages) to `platformdirs.user_log_path("ado-dashboard")`. LICENSE copyright updated `wip-dashboard` → `ado-dashboard`. `CHANGELOG.md` created (Keep-a-Changelog format). `.github/workflows/release.yml` created (OIDC/Trusted Publishing, no tokens). `RELEASING.md` created. `WIP_DASHBOARD_REPO_ROOT` deprecation message now names v0.4.0 removal. Build verified clean (`python -m build`), 79/79 tests pass. Wheel inspected — no `wip_dashboard` content. Changes bundled into Thorin's commit d677636 (parallel agent absorbed my staged files); all pushed to origin/dev.

- **Glóin Public-Readiness Audit (2026-07-17):** 8 blockers found before PyPI publication. `platformdirs` is a runtime dep missing from pyproject.toml — app will crash on first run in clean installs. pyproject.toml entirely missing `readme`, `license`, `authors`, `[project.urls]`, and `classifiers`. No CHANGELOG.md. No release.yml workflow. Log file path in `__main__.py` writes to site-packages on non-editable installs (PermissionError risk). `ado-dashboard` name available on PyPI (404). `WIP_DASHBOARD_REPO_ROOT` deprecation present but lacks removal version. No migration tooling for `~/.wip-dashboard/` → `~/.ado-dashboard/` config dirs. Go/No-Go: **NO-GO**. See `.squad/decisions/inbox/gloin-public-audit.md`.
<!-- Append new learnings below. Each entry is something lasting about the project. -->
- **Thorin OSS Scrub (2026-05-08):** Removed Microsoft-internal identifiers; introduced InvestigationLauncher Protocol adapter. Env var renamed: `BAND_REPO_ROOT` → `WIP_DASHBOARD_REPO_ROOT`. See `.squad/decisions/decisions.md`.
- **Thorin+Bofur Package Rename (2026-05-25):** Rename execution complete — `wip-dashboard` → `ado-dashboard`. Package name, CLI entry point, pyproject.toml, all imports, docs, config dirs updated. Users should run `pip install -e .` to register new CLI script. See `.squad/decisions/decisions.md` for full scope.
- **Thorin Env Var Rename Loose-Ends (2026-05-26):** Canonical env var `WIP_DASHBOARD_REPO_ROOT` → `ADO_DASHBOARD_REPO_ROOT` with backward-compat deprecation fallback. Updated `config.py`, README, and `docs/configuration.md`. See decisions.md.
