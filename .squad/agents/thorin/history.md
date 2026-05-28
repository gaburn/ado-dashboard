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

