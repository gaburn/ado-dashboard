# OSS Scrub: Remove Microsoft-Internal Identifiers

**Date:** 2025-07-17  
**Author:** Thorin (Lead/Python+Textual TUI Architect)  
**Status:** Implemented

---

## Context

wip-dashboard was built as an internal tool.  Before open-sourcing, all Microsoft-internal identifiers, hardcoded area paths, internal team names, and internal CLI tool assumptions must be removed.

## Decision

Remove all internal identifiers in a single focused session.  Deliver a fully OSS-ready codebase in one commit.

## Changes Made

### InvestigationLauncher adapter (new module: `investigation.py`)

**Problem:** `session_client.launch_investigation`, `investigation_prompts`, and `SettingsScreen` were tightly coupled to `agency copilot` — a Microsoft-internal CLI tool.

**Decision:** Introduce a `InvestigationLauncher` Protocol.  Ship `NoOpLauncher` as the default (returns generic prompts, no backend).  Keep `AgencyLauncher` in source as a reference implementation but do not activate it by default.  All call sites delegate to `get_launcher()`.

**Rationale:** Protocol-based adapter avoids fork-and-patch; external users can plug in any backend (Claude CLI, OpenAI, HTTP API, etc.) without modifying the core.

### triage_client.py — no bundled script fallback

**Problem:** `_resolve_script_path` previously fell back to a bundled `Get-TriageItems.ps1` that contained internal area paths.

**Decision:** Remove the fallback entirely.  Rename the bundled script to `Get-TriageItems.ps1.example` with placeholder values.  Raise a clear `TriageClientError` when `triage_script_path` is not configured.

**Rationale:** Silent fallback to an example script that doesn't work (wrong area paths) is worse UX than an immediate clear error.

### TRIAGE_PR_REPO config field

**Problem:** PR linkification in the triage tab hardcoded `microsoft/OS` as the repo name.  ADO PR URLs require `{org}/{project}/_git/{repo}/pullrequest/{id}` — there is no shorter valid form.

**Decision:** Add `TRIAGE_PR_REPO` config field (empty default).  Skip PR linkification when unset.

### Env var rename: BAND_REPO_ROOT → WIP_DASHBOARD_REPO_ROOT

**Decision:** New env var `WIP_DASHBOARD_REPO_ROOT`; `BAND_REPO_ROOT` still checked as deprecated fallback to avoid breaking existing users.

### Defaults cleared

- `TRIAGE_BOARD_OPTIONS`: `[]` (was internal board URLs)
- `TRIAGE_BOARD`: `""` (was internal URL)
- `INVESTIGATION_AGENT`: `""` (was `"orchestrator"` — a Microsoft-internal agent name)

## Alternatives Considered

- **Delete `AgencyLauncher` entirely:** Rejected — it serves as a concrete reference implementation showing how to wire up a real backend.  Clearly marked as an internal example.
- **Ship a `copilot` CLI adapter (non-agency):** Out of scope for this session; can be done as a follow-up by contributors.

## Files Changed

- `src/wip_dashboard/investigation.py` (new)
- `src/wip_dashboard/config.py`
- `src/wip_dashboard/setup_wizard.py`
- `src/wip_dashboard/models.py`
- `src/wip_dashboard/session_client.py`
- `src/wip_dashboard/triage_client.py`
- `src/wip_dashboard/investigation_prompts.py`
- `src/wip_dashboard/screens/detail.py`
- `src/wip_dashboard/screens/dashboard.py`
- `src/wip_dashboard/screens/settings.py`
- `src/wip_dashboard/scripts/Get-TriageItems.ps1` → `Get-TriageItems.ps1.example` (renamed + rewritten)
- `docs/triage-and-investigation.md`
- `docs/investigation.md` (new)
- `docs/configuration.md`
- `README.md`
- `LICENSE` (new — MIT)


---

# Decision: Starter Test Suite

**Status:** ✅ Complete  
**Date:** 2026-01-09  
**Decider:** Dwalin (Testing Specialist)

## Context

The wip-dashboard repo had zero committed tests. CI was wired up (`.github/workflows/ci.yml` runs `pytest -q` and tolerates exit code 5) but needed a real starter suite to establish coverage and testing patterns.

## Decision

Wrote 79 tests across 6 modules:

1. **`test_config.py`** (20 tests) — 4-layer resolution (CLI → env → file → defaults)
   - `apply_overrides()` honors namespace attrs, splits comma-separated `projects`, ignores `None`
   - `load_from_file()` only applies values when env var not set
   - `pr_url()` and `work_item_url()` build expected URLs
   - Autouse fixture resets module state between tests

2. **`test_investigation.py`** (13 tests) — InvestigationLauncher adapter
   - `NoOpLauncher` returns generic prompts, `launch()` returns `(False, error)`
   - `get_launcher()` returns default when nothing configured
   - `AgencyLauncher` prompt tests only (launch tests skipped when `agency` not on PATH)

3. **`test_investigation_prompts.py`** (10 tests) — pure prompt builders
   - `board_key_from_url()` falls back gracefully on malformed URLs
   - `build_board_investigation_prompt()` / `build_item_investigation_prompt()` produce strings with expected identifiers
   - `build_ai_triage_prompt()` mentions JSON schema fields (id, category, priority, why, action_plan)

4. **`test_triage_categorizer.py`** (21 tests) — rule-based categorization
   - Each category branch (Blocking Issue, Bug/Behavior, PR Review, Feature Request, Support Question)
   - Priority grouping: items with `priority=1..4` land in right bucket
   - Action plan generation non-empty on non-empty inputs
   - AI analysis merge preserves valid categories/priorities only

5. **`test_models.py`** (13 tests) — dataclass parsers
   - `PullRequest`/`WorkItem`/`TriageItem` parse representative ADO dicts
   - Edge cases: missing `assignedTo`, missing `priority`, HTML in `description`
   - `TriageAnalysis.from_json` parses AI response

6. **`test_triage_client.py`** (2 tests) — negative tests
   - When `triage_script_path` config is empty/None, `_resolve_script_path()` raises clear error

## Conventions

- Files in `src/tests/`, one per module, named `test_<module>.py`
- Pytest fixtures + monkeypatch; avoided heavy `unittest.mock`
- `pytest.fixture(autouse=True)` to reset module-level state in `config` tests
- All tests pass on both Windows and Linux (CI runs ubuntu-latest)
- 79 tests, each <10ms
- No new dependencies

## Consequences

- **Positive:** Establishes baseline coverage for core modules; CI now fails on regression.
- **Negative:** Textual screens, `ado_client` async, `session_client` Windows Terminal launcher, `window_focus`, `setup_wizard` remain untested (out of scope).

## Source Surprises

None. All source functions/classes matched expectations.

## Reusable Patterns

- **Autouse fixture for module state reset:** Used in `test_config.py` to reset all module-level globals between tests. Pattern can be reused for any module with module-level state.

---

# Decision: Rename app from `wip-dashboard` to `ado-dashboard`

**Date:** 2026-05-25  
**By:** Copilot (user: Copilot)  
**Status:** Accepted

## Context

After two naming brainstorms exploring mythic/mining metaphors (adit, forge, mithril) and WIP/flow concepts (standup, porch, queue, carry, bench), the user chose a literal, functional name.

## Decision

Rename `wip-dashboard` → `ado-dashboard` across package, CLI, documentation, and configuration.

## Rationale

`ado-dashboard` is honest about what the app does — it's a dashboard for Azure DevOps. Discoverable by anyone searching for "ADO" + "dashboard" without requiring a metaphor to decode. Clear, functional, memorable.

## Rejected candidates

adit, forge, mithril, standup, porch, wip, carry, bench, slate, draft, flux, deck, thread, live, hum, tally, devdesk, queue, scope, dock.

## Scope

- `pyproject.toml` — package name, project name, CLI entry point
- `src/wip_dashboard/` → `src/ado_dashboard/` (all 22 files)
- All Python imports (16 production + 6 test files)
- User-visible strings (log filenames, config dir defaults, prog name)
- `.squad/team.md` project context
- `README.md`, `CONTRIBUTING.md`, all `docs/*.md` files
- Directory rename (repo root coordination separate)

## Execution

**Thorin (2025-07-17):** Code/package scope complete. 22 source files renamed; pyproject.toml, imports, string literals updated; py_compile verified; 6 test files updated.

**Bofur (2026-07-17):** Documentation complete. README, CONTRIBUTING, 8 doc files updated with new name/paths/examples.

Follow-up flags: GitHub repo rename pending; env var name check (`WIP_DASHBOARD_REPO_ROOT` → `ADO_DASHBOARD_REPO_ROOT`); `.github/ISSUE_TEMPLATE/bug_report.md` contains user-facing references; GitHub URLs in `CODE_OF_CONDUCT.md` and `SECURITY.md` need update post-rename.

---

# Decision: PR #1 Merge Conflict Resolution Strategy

**Date:** 2026-07-17  
**Author:** Thorin (Lead Architect)  
**PR:** #1 — dev → main  
**Commit:** 57a753b

---

## Context

Branch `dev` diverged from `main` at commit `f515967` (the first commit). Main received 5 independent commits that duplicated work already done on dev (same intent, different hashes): OSS scrub, CI setup, ruff autofixes, starter test suite, README CI/license badges + LICENSE year bump. This produced 18 add/add or content conflicts on merge.

The fundamental problem: two contributors applied the same conceptual changes (rename, style, CI) to separate branches without coordinating. By the time the merge was attempted, both branches had valid but incompatible versions of the same files.

---

## Resolution Rules Applied

### 1. One side clearly supersedes the other → `git checkout --ours` or `--theirs`

Files where dev's version was strictly newer (post-rename `ado_dashboard` imports, `ado-dashboard` CLI references):
- **Tests (6):** `--ours` — dev's `ado_dashboard` imports are correct; main's `wip_dashboard` imports would fail
- **docs/ (6):** `--ours` — dev has post-rename "ADO Dashboard" branding
- **CONTRIBUTING.md:** `--ours` — post-rename `ado-dashboard` CLI references
- **.github/ISSUE_TEMPLATE/bug_report.md:** `--ours` — post-rename `ado-dashboard` CLI references
- **pyproject.toml:** `--ours` — `ado-dashboard` name, `0.2.1` version, `ado_dashboard` package scripts

Files where main's version had a distinct improvement dev lacked:
- **LICENSE:** `--theirs` — 2026 copyright year (main's update is unambiguously correct and forward)

### 2. Both sides made distinct, additive contributions → manual merge

- **README.md:** dev's "ADO Dashboard" title + `ado-dashboard` commands; main's CI workflow badge + MIT license badge. Both contributions are valuable and non-overlapping.
- **.gitignore:** dev had squad runtime ignore patterns (logs, inbox, sessions, .squad-workstream); main had squad-framework-exclusion patterns (keeping .squad/ off main entirely). Union is correct — both sets of rules are needed on the dev branch.

---

## What Was NOT Done (and why)

- Did not take main's tests — they import `wip_dashboard` which no longer exists as the active package.
- Did not take main's docs — they reference "WIP Dashboard" (old name).
- Did not lose main's CI badges — they were cherry-picked into the README merge.
- Did not take main's pyproject.toml — it would downgrade the version and revert the rename.

---

## For Future Contributors Facing Similar Branch Divergence

1. **Identify the "source of truth" for each file class.** If one branch has a rename/refactor that the other lacks, that branch owns all files touching that rename. Use `--ours` or `--theirs` wholesale.

2. **Use `git show :2:<file>` and `git show :3:<file>`** to inspect both sides before resolving. Do not trust conflict markers alone for large files.

3. **Additive-only files need union, not choice.** `.gitignore`, dependency lists, env var tables — always union. Choosing one side discards valid rules.

4. **Test after every batch of resolutions.** Running `pytest` before committing the merge caught zero regressions here, validating the `--ours` strategy for tests.

5. **`mergeable: MERGEABLE` vs `mergeStateStatus: BLOCKED`** — after resolving conflicts and pushing, MERGEABLE means no conflicts. BLOCKED means branch protection rules (required reviews) — that is expected and correct.

---

## Outcome

- All 18 conflicts resolved, 0 content lost
- 79 tests pass
- PR #1: `mergeable: MERGEABLE`
- Pushed: `dev` at `57a753b`

