# Decision: PyPI Public Prep Execution (Glóin)

**Date:** 2026-07-17  
**Agent:** Glóin (Packaging & Distribution)  
**Status:** Complete

## Context

Copilot Orchestrator requested all 8 PyPI blockers identified in `gloin-public-audit.md` be resolved before v0.2.1 release. Three agents ran in parallel: Thorin (ghost module + hygiene), Dwalin (CI/tests), Bofur (docs/README). Glóin owned packaging metadata, log path, license, CHANGELOG, release workflow, and RELEASING.md.

## Decisions Made

### 1. `pyproject.toml` PEP 621 metadata
Added `readme`, `license`, `authors`, `keywords`, `classifiers`, and `[project.urls]` as specified. Used MIT classifier (confirmed by LICENSE file). Marked `OS Independent` rather than Windows-only — the TUI itself runs cross-platform; ADO API access is the only constraint.

### 2. Dependency pins
- `platformdirs>=3.0` — made explicit (was transitive via textual, fragile).
- `textual>=3.0.0,<5` — added `<5` upper bound. Textual has a history of breaking changes on major versions; `<5` buys 1-2 years of safety without being too tight.

### 3. Log file path
Moved from `Path(__file__).resolve().parent.parent.parent / "ado-dashboard.log"` (writes to `site-packages/` on pip install — PermissionError) to `platformdirs.user_log_path("ado-dashboard") / "ado-dashboard.log"`, creating parent dirs as needed. Import added at module top (not lazy — it's a runtime dep now).

### 4. LICENSE copyright
Updated `wip-dashboard contributors` → `ado-dashboard contributors`. Year (2026) left unchanged.

### 5. CHANGELOG.md
Created from scratch in Keep-a-Changelog format. Reconstructed v0.2.1 entries from git log. Included migration note for `~/.wip-dashboard/` → `~/.ado-dashboard/` (not auto-migrated). Tagged v0.2.0 as nominal baseline.

### 6. `.github/workflows/release.yml`
OIDC Trusted Publishing — no API tokens. Three jobs: build, publish-pypi (with `environment: pypi`), github-release. Extracts CHANGELOG section for release notes via awk. Comment block at top of file documents the one-time PyPI side setup.

### 7. RELEASING.md
SemVer policy, step-by-step release checklist, pre-flight checklist, Trusted Publishing setup instructions. Concise but complete.

### 8. Deprecation removal version
`WIP_DASHBOARD_REPO_ROOT` warning updated to state planned removal in v0.4.0. Two minor versions of notice is reasonable for an env var rename.

## Outcome

- `pyproject.toml` — fully PEP 621 compliant
- `src/ado_dashboard/__main__.py` — log path safe on pip install
- `src/ado_dashboard/config.py` — deprecation warning names removal version
- `LICENSE` — copyright correct
- `CHANGELOG.md` — created
- `.github/workflows/release.yml` — created
- `RELEASING.md` — created
- 79/79 tests pass
- `python -m build` succeeds; wheel contains only `ado_dashboard/`
- Changes committed (absorbed into Thorin's commit d677636) and pushed to origin/dev
