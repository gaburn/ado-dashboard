# Project Context

- **Owner:** the team
- **Project:** wip-dashboard — a Python Textual TUI for browsing Azure DevOps work items and PRs
- **Stack:** Python 3.12+, Textual ≥3.0, `az` CLI subprocess (no HTTP library), pytest (no tests yet), pipx-installable via hatchling
- **Created:** 2026-05-08
- **Cast:** Lord of the Rings — Thorin's Company

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-08 — Architecture discovered during docs pass

**No HTTP library.** The initial history stub guessed `httpx` — wrong. All ADO communication is via `az` CLI (`asyncio.create_subprocess_exec`). Only dependency is `textual>=3.0.0`.

**Module boundaries:**
- `ado_client` — pure async subprocess wrapper around `az repos` / `az boards`; never touches config directly (reads `config.*` globals)
- `triage_client` — runs bundled `Get-TriageItems.ps1` via async subprocess; handles mixed stdout (non-JSON status lines before the JSON array)
- `session_client` — filesystem scanner for `~/.copilot/session-state/`; also owns Windows Terminal launch/resume logic (`subprocess.Popen` fire-and-forget)
- `triage_categorizer` — pure functions, no I/O; rule-based classification + AI result merge
- `triage_cache` — file I/O only; partial-write protection via trailing-`}` check
- `window_focus` — pure Win32 ctypes; zero subprocess overhead
- `config` — module globals mutated at startup by `load_from_file` + `apply_overrides`; also mutated at runtime by `SettingsScreen.action_save`

**Async pattern:** Textual `@work` decorator (exclusive where needed). Stage-1/Stage-2 loading in `_load_data` — My PRs first for fast time-to-interactive, rest via `asyncio.gather`.

**AI triage:** Fire-and-forget Copilot CLI session writes JSON to `~/.wip-dashboard/triage/<board_key>.json`; dashboard polls every 4 seconds on a Textual timer; 5-minute timeout to rule-based fallback.

**Key surprises:**
- `Get-TriageItems.ps1` embeds an inline Python heredoc to parse HTML from ADO work-item descriptions. This is the reason `parse_*.py` scratch files exist in `src/` — they were earlier prototypes.
- Setup wizard does NOT collect triage/investigation settings; those are env-var or in-app only.
- `PROJECTS` list has no env-var guard — only settable via config file, `--projects` CLI flag, or Settings screen.
- `SettingsScreen` discovers models from `agency copilot --help` stdout at runtime (parsed with regex); `@lru_cache(maxsize=1)` so it only runs once per process.
- `_discover_agents` scans both personal (`~/.copilot/agents`, `~/.claude/agents`) and repo-level (`.github/agents`, `.claude/agents`) directories dynamically.

### 2025-07-17 — OSS scrub: Microsoft-internal identifiers removed

**Scope:** All twelve scrub tasks completed in one session.

**Architecture change — InvestigationLauncher adapter:**
- Added `src/wip_dashboard/investigation.py` — `InvestigationLauncher` Protocol, `NoOpLauncher` (shipped default), `AgencyLauncher` (Microsoft-internal reference impl, still in source but clearly marked).
- `session_client.launch_investigation` is now a thin wrapper calling `get_launcher().launch(...)`.
- `investigation_prompts` functions are thin wrappers calling `get_launcher().build_*()`.
- `SettingsScreen._discover_models`/`_discover_agents` delegate to `get_launcher()`.
- Users implement the Protocol and call `set_launcher(MyLauncher())` at app startup.

**Config changes:**
- `BAND_REPO_ROOT` env var renamed to `WIP_DASHBOARD_REPO_ROOT` (BAND_REPO_ROOT still checked as deprecated fallback).
- `TRIAGE_BOARD_OPTIONS` / `TRIAGE_BOARD` defaults changed from internal URLs to `[]` / `""`.
- Added `TRIAGE_PR_REPO` config field — required for PR linkification in triage tab; empty by default.
- `INVESTIGATION_AGENT` default changed from `"orchestrator"` to `""`.

**triage_client.py:**
- `_BUNDLED_SCRIPT` removed — `_BUNDLED_EXAMPLE` is documentation only.
- `_resolve_script_path` now raises `TriageClientError` with actionable message when `triage_script_path` is not configured (no silent fallback to bundled file).

**Script:**
- `Get-TriageItems.ps1` renamed to `Get-TriageItems.ps1.example`; completely rewritten with `<YOUR_ORG>`, `<YOUR_PROJECT>`, `<YOUR_AREA_PATH>`, `<Your Team Display Name>` placeholders and a contract header.

**Gotcha — ADO PR URL form:** Requires full `{org}/{project}/_git/{repo}/pullrequest/{id}`. Shorter forms 404. Confirmed by sub-agent Balin. `TRIAGE_PR_REPO` field added to config; linkification is skipped when unset.

**Gotcha — circular imports:** `AgencyLauncher.discover_agents()` imports `from wip_dashboard import config as _config` lazily (inside method body) to avoid module-level circular imports.

**Gotcha — Textual Select widget:** Requires at least one item. When `get_launcher().discover_models()` returns `[]`, settings.py returns `[("No backend configured", "")]` as placeholder.

### 2025-07-17 — App rename: wip-dashboard → ado-dashboard

**Scope:** Code, package, and build surfaces only. Docs/README handled separately by Bofur.

**Changes made:**
- `src/wip_dashboard/` directory renamed to `src/ado_dashboard/` via `git mv` (history preserved).
- `pyproject.toml`: `name`, `[project.scripts]` entry key and module path, `[tool.hatch.build.targets.wheel] packages` all updated.
- All `wip_dashboard` import references in 16 production files + 6 test files updated to `ado_dashboard`.
- User-visible string literals updated in `.py` files:
  - `__main__.py`: docstring, `prog=`, help text print, log file path (`wip-dashboard.log` → `ado-dashboard.log`)
  - `setup_wizard.py`: `_APP_NAME` constant (`"wip-dashboard"` → `"ado-dashboard"`)
  - `config.py`: two default path defaults (`~/.wip-dashboard/...` → `~/.ado-dashboard/...`)
  - `investigation.py`: module docstring and temp dir name
- `.squad/team.md`: project title and Project Context line updated.

**Intentionally left alone:** history entries in `.squad/agents/*/history.md`, `.squad/decisions/decisions.md`, `.github/ISSUE_TEMPLATE/`, `CONTRIBUTING.md`, `README.md`, `docs/*.md` (Bofur's scope). The old `wip-dashboard.log` file at repo root if it exists (incidental artifact).

**Verification:** `python -m py_compile` on all 12 production files and 6 test files — all passed. Zero `wip_dashboard`/`wip-dashboard` hits remaining in `src/` or `pyproject.toml`.

### 2026-07-17 — Env var rename: WIP_DASHBOARD_REPO_ROOT → ADO_DASHBOARD_REPO_ROOT

**Scope:** Follow-up from app rename. Three live references found — `config.py`,
`README.md`, `docs/configuration.md`. `.squad/` history entries left alone.

**Note:** `config.py` also carried a stale intermediate name `ado_dashboard_REPO_ROOT`
(lowercase) from the prior pass — corrected to `ADO_DASHBOARD_REPO_ROOT` in the same edit.

**Backward compat:** Implemented. `WIP_DASHBOARD_REPO_ROOT` still read as deprecated
fallback (`warnings.warn(DeprecationWarning)`). ~10 lines, low risk.

**Verification:** `py_compile` on `config.py` — passed. Re-grep confirmed zero
live `WIP_DASHBOARD_REPO_ROOT` hits outside `.squad/` history files.

**Decision note:** `.squad/decisions/inbox/thorin-env-var-rename.md`

### 2026-05-28 — Config: Org URL normalization now handled at load time

**Note:** Setup wizard was saving bare organization names instead of full Azure DevOps URIs. Balin added `_normalize_org_url()` helper to `config.py` (applied in `load_from_file` and `apply_overrides`), and patched the wizard to normalize at prompt time. This is now a config layer concern — all org inputs should flow through normalization.

### 2026-05-28 — Empty-state UX pattern: Branch on configured vs. unconfigured

**Source:** Bofur's Triage tab UX fix  
**Pattern:** Never reuse one signal for two different states. Empty list from "nothing configured" must look different from empty list from "everything done."

**Application:** Triage tab now shows:
- "No triage board configured. Add one in Settings if you'd like to use Triage." when `triage_script_path` is falsy
- "No items in triage queue 🎉" when path is set and results are empty

**General rule for future features:**
1. Do not notify at startup (implies urgency or failure).
2. Use the tab/panel itself as the invitation to configure.
3. Name the cause ("not configured"), point to the fix ("Settings"), be optional in tone ("if you'd like").
4. Keep the configured-but-empty copy as a distinct, accurate message.

### 2026-07-17 — PR #1 merge conflict resolution: dev → main (18 files)

**Situation:** `dev` diverged ~18 commits from `main` after the OSS scrub and rename were re-applied to `main` independently (different hashes, same intent). Standard `git merge` produced add/add conflicts on every file first created post-divergence.

**Root cause:** `main` was updated in isolation (CI, ruff, tests, README badges, LICENSE year) without first merging `dev`. Both branches independently authored the same files with different names/imports (`wip_dashboard` on main, `ado_dashboard` on dev).

**Resolution applied (by file class):**

| Class | Rule | Rationale |
|---|---|---|
| Tests (6) | Ours (dev) | Post-rename `ado_dashboard` imports; test logic identical |
| docs/ (6) | Ours (dev) | Post-rename "ADO Dashboard" branding throughout |
| CONTRIBUTING.md | Ours (dev) | Post-rename `ado-dashboard` CLI references |
| bug_report.md | Ours (dev) | Post-rename `ado-dashboard` CLI references |
| pyproject.toml | Ours (dev) | `ado-dashboard` name, `0.2.1` version, `ado_dashboard` package |
| LICENSE | Theirs (main) | 2026 copyright year — main had the more recent update |
| README.md | Merged | Title + commands from dev; CI + license badges from main |
| .gitignore | Union | All squad runtime entries (dev) + squad-exclusion entries (main) |

**Key lesson:** When two branches independently apply the same conceptual change with different content, `git checkout --ours/--theirs` is clean and correct. Only files where both sides made **distinct, additive contributions** (README badges, .gitignore exclusion rules) needed a true manual merge.

**Outcome:** All 79 tests pass. PR #1 `mergeable: MERGEABLE`. `mergeStateStatus: BLOCKED` reflects required-review branch protection, not conflicts.

**Decision note:** `.squad/decisions/inbox/thorin-pr1-merge-resolution.md`

### 2025-07-17 — Public-readiness audit: repo hygiene + architectural review

**Scope:** Audit-only pass (no files changed). Full report at `.squad/decisions/inbox/thorin-public-audit.md`.

**Two blockers identified:**
1. `src/wip_dashboard/` (22 files) still tracked — ghost of incomplete rename that survived the PR #1 merge. `git rm -r src/wip_dashboard/` required.
2. `.squad/config.json` references `claude-opus-4.7-1m-internal` — internal model name; must be replaced with a public model or removed before main goes public.

**Key recommended fixes:**
- `.ruff_cache/` missing from `.gitignore` — gap allows accidental commit.
- `requirements.txt` is a 1-line duplicate of `pyproject.toml`; delete it.
- `~/.wip-dashboard/` in `.gitignore` is a no-op (tilde not expanded by git); remove.
- `.squad/` public-shipping decision is deferred to user: the gitignore guard is in place for main, but files are tracked on dev — `git rm` needed if the answer is "no".
- Cross-platform OS cruft patterns (`.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.tmp`, `*.bak`) missing from `.gitignore`.

**Architecture verdict:** `ado_dashboard` module shape is sound — clean boundaries, discoverable `__main__.py`, single dependency. No structural issues beyond the ghost module.

**Gotcha — log path in `__main__.py`:** Log file is written 3 levels above `__file__` which resolves to repo root during dev but to a Python lib directory when installed via pip. Should write to `~/.ado-dashboard/` instead.

### 2026-07-17 — Pre-public hygiene: ghost module removal, .squad/ pruning, .gitignore cleanup

**Scope:** Release-quality hygiene pass before PyPI ship. Decision note at `.squad/decisions/inbox/thorin-public-prep-execution.md`.

**Ghost module removed:** `src/wip_dashboard/` — 22 files (`git rm -rf`). These were the pre-rename copies that survived the PR #1 merge. They imported nothing from the live `ado_dashboard` module and were pure dead weight. No test failures after removal (79/79 pass).

**Internal model name scrubbed:** `.squad/config.json` — all four `agentModelOverrides` entries changed from `claude-opus-4.7-1m-internal` to `claude-opus-4.7`. Kept the file; it is useful for contributors who run squad locally.

**.squad/ pruning:** Removed `templates/`, `orchestration-log/`, `log/`, `casting/`, `skills/`, `identity/`, `.first-run`. Kept: `team.md`, `routing.md`, `ceremonies.md`, `decisions/decisions.md`, `config.json`, and all agent `charter.md`/`history.md` files. The `decisions/inbox/` was not tracked — no action needed.

**.gitignore updates:**
- Added `.ruff_cache/`, `*.tmp`, `*.bak`, `.DS_Store`, `Thumbs.db`, `desktop.ini`
- Added the pruned `.squad/` paths so they don't get re-tracked
- Removed no-op `~/.wip-dashboard/` line (tilde not expanded by git)

**requirements.txt deleted:** Was a 1-line file (`textual>=3.0.0`) — pure duplicate of `pyproject.toml`. Deleted via `git rm`.

**Rule confirmed:** Before any public ship, check `git ls-files | grep -i internal` and `git ls-files | grep _1m_` to catch internal model references. Also confirm no ghost module directories survive renames.

### 2026-07-17 — Demo mode: --demo flag with Tolkien fixture data

**Scope:** Full demo mode implementation (feature commit on `dev` branch).

**Architecture chosen — demo/ package with factory helpers:**
- `src/ado_dashboard/demo/` package: `fixtures.py` (all Tolkien data) + `clients.py` (`DemoAdoClient`, `DemoTriageClient`, `DemoSessionClient`) + `__init__.py` (exports).
- Three module-level factory functions in `dashboard.py` (`_demo_ado`, `_demo_triage`, `_demo_session`) return the demo client or `None` based on `config.DEMO_MODE`. Used as drop-in replacements at every call site in `_load_data` and `_refresh_triage`.
- `config.DEMO_MODE: bool` reads `ADO_DASHBOARD_DEMO` env var, set at process start.
- `--demo` CLI flag in `__main__.py` sets the env var and skips the setup wizard entirely.

**Fixture data policy — obviously fictional:**
- Org: `https://dev.azure.com/middle-earth`, project: `expedition`.
- Demo user: `g.grey@middle-earth.example` (Gandalf). All reviewer emails use `@middle-earth.example`.
- No `microsoft.com`, no real ADO URLs, no internal strings. Verified by `TestFixtureContentSafety`.

**Triage categorization:** Pre-set `category`/`ai_why` on `TriageItem` instances directly (slots=True dataclass supports this). `categorize_triage_items()` may overwrite `category` but `ai_why` survives, giving rich triage display.

**`_populate_reviewing_table` email fix:** Promoted from `config.USER_EMAIL` to `user_email: str = ""` parameter (with `email = user_email or config.USER_EMAIL` fallback). Backward-compatible — all existing call sites continue to work; demo mode passes `DEMO_USER_EMAIL` explicitly.

**AI enrichment skip:** `_load_data` Stage 2 and `_refresh_triage` both guard `_start_ai_enrichment()` with `not config.DEMO_MODE` — no Copilot subprocess invoked in demo mode.

**Testing:** 38 new tests in `src/tests/test_demo_mode.py` (156 total, all pass). Coverage: fixture shapes, model types, varied states, demo client method return types, factory behavior, subprocess-never-called assertions, content safety.

**Key gotcha — `@staticmethod` with module-level state:** Can still access `config.USER_EMAIL` inside the body, but if you need the caller to pass a *different* email (demo mode), you must add a parameter. Pattern: `user_email: str = ""` with `email = user_email or config.MODULE_DEFAULT`.



**Audit + execution phase final state:** Five parallel audits (Thorin, Balin, Dwalin, Bofur, Glóin) identified 20 total issues (1 blocker per agent track + 2–8 recommended + polish). Four parallel execution agents (Thorin, Dwalin, Bofur, Glóin) resolved all blockers and most recommended fixes in single commits:
- Thorin: d677636 (hygiene, ghost module, .squad/ pruning, .gitignore hardening, requirements.txt delete)
- Bofur: ec7404e (README/CONTRIBUTING/CODE_OF_CONDUCT/templates fixes)
- Dwalin: bcaf610 (39 ado_client tests, CI matrix expansion Ubuntu+Windows × 3.12+3.13, pre-commit config)
- Glóin: 27201cb (pyproject.toml PEP 621 metadata, log path fix, CHANGELOG, release.yml, RELEASING.md)
- Coordinator: b23e463 (PR #1 merge verification + health report)

**118 tests pass** (39 new + 79 existing, all under 1s). CI matrix green on all 4 jobs. PR #1 merge conflicts resolved; `mergeable: MERGEABLE` status. No secrets, no ghost code, no internal references in committed tree. `.squad/` partially shipped (decision + routing + ceremonies + team + agent charters + history; scaffolding removed).

**Two follow-up items flagged but not blocking release:**
1. Bofur: README screenshot/GIF (UX win, not functional blocker)
2. Bofur: CODE_OF_CONDUCT maintainer email placeholder (flagged in <!-- TODO --> comment)

**Public ship readiness: READY** (all 8 Glóin blockers resolved; Dwalin blocker on ado_client coverage resolved; Bofur blocker on README clone step resolved; Thorin blockers on ghost module + internal refs resolved).

