# Decision: Dwalin Public-Prep Execution

**Date:** 2026-07-17  
**Author:** Dwalin (Testing Specialist)  
**Status:** Done

## What was done

### 1. `src/tests/test_ado_client.py` — 39 new tests

`ado_client.py` had zero coverage. Now covered:

| Area | Tests |
|---|---|
| `_run_az` success (dict, list, empty, whitespace stdout) | 4 |
| `_run_az` failures (az not on PATH, non-zero exit, malformed JSON, --output json flag) | 4 |
| `_raise_helpful_error` (login, connection error, missing extension ×3, generic, long stderr) | 7 |
| `_fetch_prs_for_project` (happy path, non-list response) | 2 |
| `fetch_my_prs` (happy path, empty, multi-project, sparse fields) | 4 |
| `fetch_reviewing_prs` (happy path, reviewer votes, declined reviewer) | 3 |
| `fetch_pr_detail` (happy path, invalid response type) | 2 |
| `fetch_work_items` (happy path, empty, WIQL error dict, tags, parent_id) | 5 |
| `_fetch_work_items_by_ids` (empty, happy path, non-list) | 3 |
| `fetch_work_item_detail` (happy path, invalid response type) | 2 |
| `fetch_work_items_with_hierarchy` (no parents, missing parent fetch, skips known parents) | 3 |

**Mock boundary:** `asyncio.create_subprocess_exec` (via `unittest.mock.patch`) and `shutil.which`. No real `az` invocations.

**Total suite after:** 118 tests (39 new + 79 existing), all pass, <1s.

### 2. CI matrix expansion (`.github/workflows/ci.yml`)

- Removed stale exit-5 escape hatch (`pytest -q || ([ $? -eq 5 ] && ...)`)
- Replaced single `runs-on: ubuntu-latest` with OS/Python matrix
- Matrix: `os: [ubuntu-latest, windows-latest]` × `python-version: ['3.12', '3.13']` = 4 jobs
- `fail-fast: false` so all combinations run even if one fails
- Added soft-fail coverage gate: `pip install pytest-cov` + `pytest --cov=ado_dashboard --cov-fail-under=60`
- TODO comment flags Glóin to add `pytest-cov` to `[dev]` extras in pyproject.toml

### 3. `.pre-commit-config.yaml`

- Added at repo root
- Hooks: `ruff` (lint, with `--fix`) and `ruff-format`
- Pinned to `astral-sh/ruff-pre-commit@v0.8.4`
- Comment instructs `pre-commit install`; Bofur to reference in CONTRIBUTING.md

## Key decisions

- **`asyncio.run()` in sync tests** — avoids pytest-asyncio dependency (not in pyproject.toml dev extras). Synchronous wrapper is simple and has no interaction with Textual's event loop.
- **`patch("shutil.which")` not `patch("ado_dashboard.ado_client.shutil.which")`** — module uses `import shutil; shutil.which(...)` so patching the stdlib directly is correct.
- **Soft-fail on coverage gate** — 60% threshold with `|| echo ::warning::` pattern. Non-blocking until Glóin lands pyproject changes and threshold can be raised.
- **`fail-fast: false` on matrix** — Windows runner failures must not mask Linux results during rollout.
