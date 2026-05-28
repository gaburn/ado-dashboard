# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — Textual TUI for Azure DevOps work items and PRs
- **Stack:** Python 3.11+, pytest, Textual Pilot, snapshot testing, GitHub Actions CI
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->
- **Thorin OSS Scrub (2026-05-08):** Removed Microsoft-internal identifiers; introduced InvestigationLauncher Protocol adapter. Env var renamed: `BAND_REPO_ROOT` → `WIP_DASHBOARD_REPO_ROOT`. See `.squad/decisions/decisions.md`.
- **Starter Test Suite (2026-01-09):** 79 tests covering config (4-layer resolution), investigation (adapter interface), prompts, categorizer (rule-based), models (parsers), and triage_client (error handling). Conventions: pytest fixtures + monkeypatch, autouse fixture for config state reset, ~79 tests (<10ms each). No source surprises.
