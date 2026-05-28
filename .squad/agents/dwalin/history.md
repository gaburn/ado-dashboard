# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, pytest, Textual Pilot, snapshot testing, GitHub Actions CI
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->
- **Thorin OSS Scrub (2026-05-08):** Generified internal identifiers; introduced InvestigationLauncher Protocol adapter. Legacy env var renamed to `WIP_DASHBOARD_REPO_ROOT`. See `.squad/decisions/decisions.md`.
- **Starter Test Suite (2026-01-09):** 79 tests covering config (4-layer resolution), investigation (adapter interface), prompts, categorizer (rule-based), models (parsers), and triage_client (error handling). Conventions: pytest fixtures + monkeypatch, autouse fixture for config state reset, ~79 tests (<10ms each). No source surprises.
- **Public-Prep Execution (2026-07-17):** Wrote 39 tests for `ado_client.py` (zero → full coverage of all public functions and error paths). Patched at `asyncio.create_subprocess_exec` and `shutil.which` — no real `az` calls. Total suite: 118 tests, 0 failures. Removed stale exit-5 escape hatch from CI. Added `windows-latest` and Python 3.13 to CI matrix (4 job matrix: 2 OS × 2 Python). Added soft-fail coverage gate (`--cov-fail-under=60`) with bridge `pip install pytest-cov`; TODO comment flags Glóin to add dep to pyproject. Added `.pre-commit-config.yaml` with `ruff` + `ruff-format` hooks (astral-sh/ruff-pre-commit v0.8.4). Ruff clean. Committed as one atomic commit.
- **Issue #3 Tracks Assigned (2026-05-28):** Thorin decomposed Issue #3 (work item field editing) into 4 sub-tracks. **Dwalin track #3-d:** Tests — unit + Pilot integration tests for all edit screens and save workers. No blockers.
- **Issue #3 Test Plan Authored (2026-07-17):** Wrote `.squad/decisions/inbox/dwalin-issue-3-test-plan.md` covering 25 API cases, 17 screen cases, 8 snapshots, 2 slow integration cases; posted to issue #3. **Key constraint discovered:** existing `ado_client.py` uses `asyncio.create_subprocess_exec` against `az` CLI — NOT httpx. Plan mocks at the subprocess boundary (consistent with `test_ado_client.py`), with a switch-to-respx contingency if Balin's spike #3-e moves any function to raw REST. Coverage targets: 100% on new `ado_client` functions, ≥90% on `screens/edit.py`, project floor raised 60→70%. 10 open questions flagged (Q1 worker-collision semantics → Thorin, Q2 snapshot terminal size → Bofur, Q3/Q4/Q5/Q9 API shape → Balin, Q6/Q7 bindings & visuals → Bofur). Fixture list (12 entries) gated on Balin's API skeleton landing. No code yet — by design.
