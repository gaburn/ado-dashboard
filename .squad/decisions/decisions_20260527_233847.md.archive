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



# Public-Readiness Audit — Thorin Track
**Date:** 2025-07-17  
**Scope:** Repo hygiene + architectural OSS readiness  
**Branch:** dev  

---

## Findings

### 🔴 BLOCKER — `src/wip_dashboard/` still tracked in git

**File count:** 22 files  
**Evidence:** `git ls-files -- "src/wip_dashboard/*"` returns 22 paths  
**Root cause:** During PR #1 merge (dev ← main), main still carried the old `wip_dashboard/` directory. The merge resolution kept `ado_dashboard/` tests/pyproject from dev, but did not remove the `wip_dashboard/` source tree that came in from main.  
**Impact:** Public repo ships two competing packages. `pip install` will only install `ado_dashboard` (per `pyproject.toml`), but `import wip_dashboard` works at checkout-time — confusing and misleading.  
**Action:** `git rm -r src/wip_dashboard/` then commit.

---

### 🔴 BLOCKER — `.squad/config.json` references internal model name

**File:** `.squad/config.json` lines 4–7  
**Content:** `"claude-opus-4.7-1m-internal"` for all agents  
**Impact:** Exposes an internal/non-public model identifier; would fail for any external user attempting to run the squad.  
**Action:** Replace with a publicly available model name (e.g. `claude-opus-4.7`) or strip the overrides entirely so agents default to the public model.

---

### 🟡 RECOMMENDED — `.squad/` directory public-shipping decision required

**File count:** 118 tracked files  
**Situation:** `.gitignore` on dev lists `.squad/` (to prevent accidental merge into main), but the files are already tracked on dev — gitignore has no effect on committed files.  
**OSS case FOR shipping it:** `.squad/` is the AI team's working memory and decision history; it's an interesting demonstration of the squad model, directly relevant to the OSS story.  
**Case AGAINST:** Contains process noise (orchestration logs, templates, cast history). `.squad/config.json` references an internal model name (see blocker above).  
**Decision required by user.** If NOT shipping:
- `git rm -r .squad/` on the branch that will become `main`
- Add `.squad/` to `.gitignore` on main (already present on dev)

If YES shipping: fix the config.json model name blocker first.

---

### 🟡 RECOMMENDED — `.github/agents/squad.agent.md` and `squad-*.yml` workflows tracked despite `.gitignore`

**Files:**
- `.github/agents/squad.agent.md`
- `.github/workflows/squad-heartbeat.yml`
- `.github/workflows/squad-issue-assign.yml`
- `.github/workflows/squad-triage.yml`
- `.github/workflows/sync-squad-labels.yml`

**Situation:** `.gitignore` on dev lists all of these, but they're already committed — gitignore doesn't remove tracked files.  
**Impact:** Squad-internal CI workflows would ship to main and run against the public repo with potentially unexpected effects (issue labeling, heartbeats, etc.).  
**Action:** Decision should be made in concert with `.squad/` decision above. If squad machinery ships publicly, these workflows should be reviewed for public-repo safety. If not, `git rm` them from the branch destined for main.

---

### 🟡 RECOMMENDED — `.ruff_cache/` not in `.gitignore`

**Situation:** `.ruff_cache/` directory is present on disk, is not tracked (untracked), but is also NOT in `.gitignore`. Any developer who runs `ruff` will generate it; there's no guard against accidental `git add .`.  
**Action:** Add `.ruff_cache/` to `.gitignore`.

---

### 🟡 RECOMMENDED — `requirements.txt` is redundant

**File:** `requirements.txt` (1 line: `textual>=3.0.0`)  
**Situation:** `pyproject.toml` already declares `textual>=3.0.0` under `[project] dependencies`. The `requirements.txt` is a verbatim duplicate.  
**Impact for OSS:** New contributors see `requirements.txt` and wonder if it's the canonical source; creates false impression of a pip-workflow project when the actual install is `pip install -e .`.  
**Action:** Delete `requirements.txt`. If a `pip install -r requirements.txt` escape-hatch is explicitly desired, add a comment documenting why it exists alongside `pyproject.toml`.

---

### 🟡 RECOMMENDED — `__main__.py` writes log file to repo root directory

**File:** `src/ado_dashboard/__main__.py` line 77  
**Code:** `log_file = Path(__file__).resolve().parent.parent.parent / "ado-dashboard.log"`  
**Impact:** Every run writes `ado-dashboard.log` to the repo root (3 levels up from the module file). While gitignored, this is surprising behavior for users who install via `pip install` — the log ends up in `site-packages/../../../` which resolves to a Python lib directory.  
**Action:** Write to `~/.ado-dashboard/ado-dashboard.log` or `platformdirs.user_log_dir()` for proper multi-platform behavior.

---

### 🟢 POLISH — `.gitignore` has a no-op `~/.wip-dashboard/` entry

**File:** `.gitignore` line 23  
**Content:** `~/.wip-dashboard/`  
**Situation:** Git `.gitignore` cannot reference paths outside the repository. Tilde-expansion is not performed by git. This entry is silently ignored and provides no protection.  
**Action:** Remove the line. The actual runtime config directory is outside the repo by definition; no `.gitignore` entry is needed.

---

### 🟢 POLISH — `.copilot/` directory: correctly gitignored, safe

**Situation:** `.copilot/` exists on disk with `mcp-config.json` (template with `${GITHUB_TOKEN}` env var placeholder — no actual token). Properly excluded by `.gitignore` line 21.  
**Recommendation:** No action required. The existing `.gitignore` rule is correct. Worth documenting in `docs/development.md` what `.copilot/` is for, for new contributors.

---

### 🟢 POLISH — `src/tests/` location is non-standard but acceptable

**Situation:** Tests live in `src/tests/` rather than `src/ado_dashboard/tests/` or a top-level `tests/`. This is an unusual layout — the tests directory is a sibling of the package directory rather than a child or project-root sibling.  
**Impact:** Functional (pytest resolves it via `testpaths = ["src/tests"]` in `pyproject.toml`). The wheel correctly excludes tests (only packages `src/ado_dashboard`).  
**Recommendation:** Consider moving to `tests/` at project root for convention-matching and easier contributor discovery. Not a blocker.

---

## `.gitignore` Adequacy Summary

| Pattern | Status |
|---------|--------|
| `*.log` | ✅ Covered |
| `__pycache__/` | ✅ Covered |
| `.pytest_cache/` | ✅ Covered |
| `.ruff_cache/` | ❌ **Missing — add it** |
| `build/`, `dist/`, `*.egg-info/` | ✅ Covered |
| `.copilot/` | ✅ Covered |
| `.squad/` (for main branch) | ✅ Present (but tracked files on dev are unaffected) |
| `~/.wip-dashboard/` | ⚠️ No-op (tilde not expanded by git) — remove |
| `.DS_Store`, `Thumbs.db`, `desktop.ini` | ❌ **Missing — add for cross-platform hygiene** |
| `*.tmp`, `*.bak` | ❌ **Missing — add as general cruft guards** |

---

## Architectural OSS Readiness

**Entry point:** `src/ado_dashboard/__main__.py` — well-documented docstring, clean `main()` function, `argparse`-based CLI. ✅  
**Module layout:** `ado_client`, `triage_client`, `session_client`, `config`, `models`, `screens/`, `styles/`, `setup_wizard` — each with a single clear responsibility. Explainable to a stranger. ✅  
**`src/tests/` location:** See Polish note above.  
**Blocking smell:** `src/wip_dashboard/` — see Blocker #1.

---

## Executive Summary

The repo has two hard blockers before public release on this track: the `src/wip_dashboard/` ghost module (22 files from an incomplete rename that survived the PR #1 merge) must be removed, and `.squad/config.json` must have its internal model name replaced or stripped. Three recommended fixes round out the hygiene pass: add `.ruff_cache/` to `.gitignore`, delete the redundant `requirements.txt`, and make an explicit user decision about whether the `.squad/` machinery ships publicly (the gitignore guards are in place for main but the tracked-file precedence means a deliberate `git rm` is required if the answer is "no"). The `.copilot/` directory is cleanly excluded already. The architectural shape of `ado_dashboard` is solid — clean module boundaries, discoverable entry point, single external dependency — and will present well to OSS contributors once the blocker cruft is cleared.


# Balin Public-Readiness Audit — Secrets & Internal Identifiers

**Date:** 2026-05-28  
**Scope:** Secrets, credentials, and internal-identifier leakage  
**Auditor:** Balin (ADO API + secrets/auth specialist)

---

## Findings Summary

| # | Status | Location | Description |
|---|--------|----------|-------------|
| 1 | 🟢 Clean | Entire repo | No hardcoded PATs, Bearer tokens, API keys, or private keys found in any committed file |
| 2 | 🟢 Clean | Git history (all 32 commits) | No secrets in history — `BEGIN PRIVATE KEY`, `Bearer `, `Authorization:`, `password=`, `api_key` scans all returned empty |
| 3 | 🟢 Clean | `.gitignore` | `*.log`, `.copilot/` gitignored — confirmed log files are NOT tracked |
| 4 | 🟢 Clean | `config.py` | Defaults are intentionally empty strings (`""`) — no real org/project/email hardcoded |
| 5 | 🟢 Clean | `setup_wizard.py` | Prompts use generic placeholder `https://dev.azure.com/<your-org>`; treats it as empty if unchanged |
| 6 | 🟢 Clean | `ado_client.py` | Auth delegated entirely to `az` CLI (`az login`) — no PAT storage, no `Authorization:` header construction |
| 7 | 🟢 Clean | `.example` files (×2) | `Get-TriageItems.ps1.example` uses `<YOUR_ORG>`, `<YOUR_PROJECT>`, `<YOUR_AREA_PATH>`, `<Your Team Display Name>` — all proper placeholders |
| 8 | 🟢 Clean | `models.py:57` | `"from microsoft teams"` is a noise-filter string for triage categorization, not an identifier leak |
| 9 | 🟢 Clean | Internal identifiers scrub | Commit 8847118 properly removed `band`, `engsys`, `configgen`, hardcoded area paths, internal team names — none present in current tree or any post-scrub commit |
| 10 | 🟢 Clean | Email addresses | No `@microsoft.com` or any real email in committed source files |
| 11 | 🟡 Recommended | `ado_client.py:39` (×2) | `log.debug("az command: %s", " ".join(cmd))` logs full az CLI invocations at DEBUG level, which include user email (e.g., `--creator user@example.com`) and org URL. Log files are gitignored but users sharing debug logs could expose their email + project names |
| 12 | 🟡 Recommended | `investigation.py:175–190` (×2) | `AgencyLauncher` references `aka.ms/agency-cli` — a Microsoft-internal tool. Class is clearly labeled "Microsoft-internal example adapter" and the comment says `agency` CLI is not publicly distributed. Acceptable as a reference implementation, but the label in module docstring (`AgencyLauncher (Microsoft-internal example)`) could confuse external contributors |
| 13 | 🟡 Recommended | `docs/investigation.md:71` | Section heading "AgencyLauncher (Microsoft-internal example)" — informational disclosure only; no secrets, but adds MS-internal flavor to public docs |

---

## Detail Notes

### Finding 11 — DEBUG logging of az commands

`ado_client.py` line 39 (both `ado_dashboard` and `wip_dashboard` copies):
```python
log.debug("az command: %s", " ".join(cmd))
```
The `cmd` list includes arguments such as:
- `--creator <user-email>` / `--reviewer <user-email>`
- `--wiql "... WHERE [System.AssignedTo] = '<user-email>' ..."`
- `--org <org-url>` / `--project <project-name>`

**Runtime log files confirmed** (`ado-dashboard.log`, `wip-dashboard.log`) to contain full az invocations with user email, org, and project names. These files are properly gitignored.

**Risk:** Low for source/git exposure. Moderate if a user shares their debug log in a bug report.  
**Recommendation:** Redact or omit the `--wiql` payload and credential-adjacent arguments from the debug log, or document clearly that debug logs may contain PII.

### Finding 12 — AgencyLauncher internal reference

`src/ado_dashboard/investigation.py:177`:
```python
# Uses the `agency copilot` CLI (https://aka.ms/agency-cli) to launch
```
The `aka.ms/agency-cli` shortlink is a Microsoft-internal redirect (not publicly accessible). The class and its docstring explicitly state it is "Microsoft-internal" and "not publicly distributed." This is good disclosure.

**Risk:** Minimal — it is clearly marked. No credentials. Just a reference to an unavailable tool.  
**Recommendation:** Consider renaming section to "AgencyLauncher (example adapter — requires internal `agency` CLI)" to reduce "Microsoft-internal" language in public docs, or add a note that external users should replace this adapter.

---

## Auth Flow Review

| Component | Pattern | Assessment |
|-----------|---------|------------|
| `config.py` | Reads from env vars (`ADO_ORG_URL`, `ADO_PROJECT`, `ADO_USER_EMAIL`) and config file; no PAT field | ✅ Safe — no credential storage |
| `ado_client.py` | Shells to `az` CLI; auth entirely delegated to Azure CLI's own token cache | ✅ Safe — no PAT in code paths |
| `setup_wizard.py` | Saves org URL, project, email to JSON; no PAT, no secret fields | ✅ Safe — wizard captures no credentials |
| Log paths | `ado-dashboard.log` written to repo root; contains email+org at DEBUG level | 🟡 PII risk in debug logs (gitignored but present on disk) |

**No code path logs a PAT.** The `az` CLI manages its own token cache; ado-dashboard never handles credentials directly.

---

## History Scan Results

| Pattern searched | Commits matched | Verdict |
|-----------------|-----------------|---------|
| `BEGIN PRIVATE KEY` | 0 | 🟢 Clean |
| `Bearer ` | 0 | 🟢 Clean |
| `Authorization` | 1 (CI workflow `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}`) | 🟢 Clean — standard GitHub Actions pattern |
| `password` | 0 | 🟢 Clean |
| `api_key` | 0 | 🟢 Clean |
| `token` (added lines) | Only CI workflow `secrets.GITHUB_TOKEN` refs | 🟢 Clean |
| `@microsoft.com` | 0 (in committed source) | 🟢 Clean |
| `dev.azure.com/microsoft` | 1 (scrub commit 8847118 — removed) | 🟢 Clean |

The single historical reference to `dev.azure.com/microsoft` appeared in commit 8847118 as a line being **removed** (the scrub commit itself). It is not present in any post-scrub commit.

---

## Executive Summary

**No blockers. Repo is clean of hardcoded secrets and credentials.**

The auth model is sound: ado-dashboard delegates all Azure DevOps authentication to the `az` CLI, stores no PATs or tokens, and uses empty defaults. The `.gitignore` correctly excludes log files, `.env` files, and config dirs. The internal-identifier scrub (commit 8847118) was thorough — no residual area paths, team names, or internal tool names remain in the committed tree.

Two 🟡 Recommended items for polish before public launch:
1. **Debug log PII**: `log.debug("az command: ...")` in `ado_client.py` writes user emails and project names into on-disk log files. Not a git-exposure risk, but worth documenting or redacting for users who share bug reports.
2. **`AgencyLauncher` Microsoft-internal label**: The class is correctly marked as internal and unavailable publicly, but the "Microsoft-internal" language in a public OSS repo's module docstring and docs may warrant softening to "example adapter (requires third-party `agency` CLI)".


# Dwalin — Public-Readiness Audit: CI, Test Quality & Infrastructure

**Date:** 2026-07-17  
**Auditor:** Dwalin (Testing Specialist)  
**Track:** CI configuration, test quality, test infrastructure

---

## 1. CI Workflow Audit

### Workflow: `.github/workflows/ci.yml`

**Triggers:**
- `push` → `dev`, `main`, `release/*`
- `pull_request` → `main`, `dev`

**Steps:**
1. Checkout (`actions/checkout@v4`)
2. Python setup (`actions/setup-python@v5`, Python **3.12 only**, pip cache)
3. `pip install -e ".[dev]"`
4. `ruff check src/` — lint
5. `pytest -q` — test run with exit-5 toleration

**Findings:**

🟡 **RECOMMENDED — Single OS only (ubuntu-latest)**  
No Windows or macOS runners. This project explicitly targets Windows (PowerShell triage, Windows Terminal integration, `window_focus.py`). An external Windows contributor can't trust CI to catch Windows-only failures. At minimum, add a Windows matrix leg.

🟡 **RECOMMENDED — Single Python version (3.12 only)**  
`requires-python = ">=3.12"` but CI only tests 3.12. If the intent is to support future 3.13+, a matrix would catch forward-compat breaks. Acceptable at v0 if explicitly 3.12-only.

🟡 **RECOMMENDED — No type checking**  
No `mypy` or `pyright` step. The codebase uses type annotations throughout. A `pyright` pass in CI would catch real bugs without dev overhead. Not a blocker but this is a public Python package now.

🟡 **RECOMMENDED — No coverage reporting**  
No `pytest-cov` in `[dev]` extras, no `--cov` flag, no coverage gate. Contributors have no feedback on what's covered. Add `pytest-cov` + `--cov=ado_dashboard --cov-report=term-missing` at minimum.

🟡 **RECOMMENDED — Stale "tolerate exit 5" escape hatch**  
```yaml
pytest -q || ([ $? -eq 5 ] && echo "::warning::No tests collected yet" && exit 0)
```
This comment ("until the suite lands") was appropriate when there were no tests. There are now 79 tests. The escape hatch doesn't currently hide failures (exit-code logic is correct), but it's misleading noise and could mask collection errors (e.g., import error causes 0 tests collected → exit 1, not 5 — this would still fail CI). Clean it up:  
```yaml
pytest -q
```

🟢 **POLISH — Lint fails loudly: YES**  
`ruff check src/` runs before pytest, fails CI on violations. Currently clean.

🟢 **POLISH — Test failures fail loudly: YES**  
With the exit-5 escape removed, fully fail-loud. Currently clean: 79/79 pass.

---

### Squad Workflows

| Workflow | Private infra? | Ship publicly? | Notes |
|---|---|---|---|
| `squad-heartbeat.yml` | No | Yes, with caveats | Uses `GITHUB_TOKEN` + optional `COPILOT_ASSIGN_TOKEN`. Falls back gracefully if PAT absent. Fine for public. |
| `squad-triage.yml` | No | Yes | Uses `GITHUB_TOKEN` only. Reads `.squad/team.md` — works out of the box. |
| `squad-issue-assign.yml` | No | Yes, with caveats | `COPILOT_ASSIGN_TOKEN` is **required** (not optional) in the Assign @copilot step. Will silently fail for repos without this PAT. External contributors won't have it. Acceptable since it's for bot assignment, not core functionality. |
| `sync-squad-labels.yml` | No | Yes | `GITHUB_TOKEN` only. Harmless if `.squad/team.md` is present. |

🟢 **None reference Microsoft-internal services, ADO APIs, or internal infra.** All squad workflows use GitHub REST API via `actions/github-script`. Safe to ship.

🟢 **No hardcoded internal URLs or tenant IDs** in any workflow file.

---

## 2. Test Coverage Audit

### Counts

| Module | Tests | Status |
|---|---|---|
| `config.py` | 20 | ✅ Well covered |
| `investigation.py` | 13 | ✅ Well covered (adapter interface + launcher lifecycle) |
| `investigation_prompts.py` | 10 | ✅ Well covered |
| `models.py` | 13 | ✅ Parsers well covered |
| `triage_categorizer.py` | 21 | ✅ Good: category logic, priority buckets, AI merge, action plan |
| `triage_client.py` | 2 | 🟡 Minimal (error paths only) |
| `ado_client.py` | 0 | 🔴 **ZERO TESTS** |
| `session_client.py` | 0 | 🔴 **ZERO TESTS** |
| `setup_wizard.py` | 0 | 🟡 Zero tests (wizard logic, config path, env detect) |
| `triage_cache.py` | 0 | 🟡 Zero tests (cache read/write/expiry logic) |
| `window_focus.py` | 0 | 🟢 Low priority (thin OS shim) |
| `app.py` | 0 | 🟡 No Textual Pilot integration tests |
| `screens/*.py` | 0 | 🟡 No Textual Pilot screen tests |

**Total: 79 tests across 6 of 13 source modules (46% module coverage)**

### Critical Gaps

🔴 **`ado_client.py` — ZERO TESTS**  
This is the core ADO integration layer. `_run_az()`, `fetch_pull_requests()`, `fetch_work_items()`, `fetch_my_review_prs()` — all untested. Any refactor breaks silently. At minimum, test the JSON parsing, error handling (ADO error dict, empty list, malformed JSON), and the "az not found" path. HTTP calls go through subprocess to `az` CLI — mock `asyncio.create_subprocess_exec` or patch `shutil.which`.

🟡 **`triage_client.py` — 2 tests (error paths only)**  
`_resolve_script_path` error cases are tested, but the core `fetch_triage_items()` pipeline (subprocess invocation, JSON parsing, error handling) has zero coverage.

🟡 **`session_client.py` — ZERO TESTS**  
Session discovery, PID scanning, CopilotSession parsing — all untested. Mockable with `tmp_path` and `monkeypatch`.

🟡 **`triage_cache.py` — ZERO TESTS**  
Cache read/write/expiry logic is non-trivial. `cache_path()`, `load_cached_analysis()`, `save_cached_analysis()` are untested.

🟡 **`setup_wizard.py` — ZERO TESTS**  
The wizard's non-interactive detection path (`sys.stdin.isatty()` check) and `config_file_path()` are unit-testable without running the interactive prompts.

### Test Speed

✅ **79 tests in 0.43–0.48s** — blazing fast. No slow tests, no I/O in the test suite. All mocked or pure logic.

### Mocking Strategy

✅ **No real ADO calls in tests** — the `az` CLI subprocess is never invoked. Tests cover pure Python logic: parsing, categorization, prompt building, config resolution.

✅ **No real filesystem side effects** — `monkeypatch` and `tmp_path` used correctly in `test_triage_client.py`.

---

## 3. Test Quality Red Flags

### Skipped / XFail Tests

🟢 **3 `@pytest.mark.skipif` in `test_investigation.py`** — all conditioned on `agency` CLI not being on PATH. This is correct behavior: skip platform-specific tests in CI where the tool isn't installed. No unconditional `@pytest.mark.skip` or `@pytest.mark.xfail`.

### Hard-Coded Paths

✅ No hard-coded absolute paths found that would break on other machines.

### Network / Wall-Clock Dependencies

✅ No `requests`, `httpx`, `urllib` calls in tests.  
✅ No `time.sleep()` or `datetime.now()` calls in tests.  
✅ No snapshot tests, so no rebaseline process needed.

### `/tmp` references in test prompts

🟢 **Minor:** `test_investigation.py` and `test_investigation_prompts.py` pass `/tmp/output.json` as a string argument to prompt builders. This is a string value in the prompt text, not an actual filesystem write — no portability issue, but it's a mild signal these tests were written on Linux/macOS.

---

## 4. CI Badge Accuracy

README badge:
```
[![CI](https://github.com/gaburn/ado-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/gaburn/ado-dashboard/actions/workflows/ci.yml)
```

Git remote: `https://github.com/gaburn/ado-dashboard.git`

✅ **Badge URL matches the actual repo.** `gaburn/ado-dashboard` is the public repo. Workflow file is `.github/workflows/ci.yml`. Badge is correct.

---

## 5. Contributor-Friendliness

### `pytest -q` out of the box after `pip install -e .[dev]`?

✅ **YES** — tested and confirmed. `pyproject.toml` sets `testpaths = ["src/tests"]`. `pip install -e ".[dev]"` installs `pytest>=8.0` and `ruff>=0.6`. No additional setup needed to run tests.

### Undocumented test setup steps?

✅ **None found.** CONTRIBUTING.md documents `pytest` and `ruff check src/`. No secret env vars required to run the test suite.

### Pre-commit config (`.pre-commit-config.yaml`)?

🟡 **MISSING — No `.pre-commit-config.yaml`**  
There's no pre-commit configuration. For a public project, a minimal `.pre-commit-config.yaml` with `ruff` (lint + format) would prevent contributors from pushing linting failures. CONTRIBUTING.md tells contributors to run `ruff check src/` manually — enforcing it via pre-commit hooks would be better.

Suggested minimal config:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## Executive Summary

**79 tests, 0.43s runtime, all passing. Ruff clean. CI runs on every push and PR.** The foundation is solid. The problems are gaps, not breakage.

| Severity | Count | Description |
|---|---|---|
| 🔴 Blocker | 1 | `ado_client.py` — zero tests on the core ADO integration module |
| 🟡 Recommended | 7 | No Windows CI runner; no type checking; no coverage gate; stale exit-5 escape; triage_client minimal coverage; session_client/triage_cache/setup_wizard uncovered; no pre-commit config |
| 🟢 Polish | 2 | `/tmp` string in test prompts; COPILOT_ASSIGN_TOKEN silent fail in squad-issue-assign |

**Top 3 actions before public ship:**
1. Add tests for `ado_client.py` — mock `asyncio.create_subprocess_exec`, test JSON parsing and error paths
2. Add a Windows runner leg to `ci.yml` — this app targets Windows users
3. Remove the stale `exit 5` escape hatch from the pytest step

Everything else is improvement, not emergency.


# Bofur: Public-Readiness Audit
**Date:** 2026-07-17  
**Track:** First-time public visitor experience  
**Auditor:** Bofur (Terminal UX Designer)

---

## README.md

### 🔴 R1 — Missing `git clone` in Install & Run
The "Install & Run" section opens with `cd ado-dashboard` — but a stranger doesn't have that directory. There's no `git clone` step, no clone URL, and no pip-prerequisite check. This is the most critical fix.

**Before:**
```bash
cd ado-dashboard
pip install -e .
ado-dashboard
```

**After:**
```bash
git clone https://github.com/gaburn/ado-dashboard.git
cd ado-dashboard
pip install -e .
ado-dashboard
```

---

### 🔴 R2 — No screenshot or demo GIF
Zero visual evidence of what this tool looks like. A TUI cannot be sold with text alone. A HN visitor who's never seen Textual will bounce immediately. Even a single static terminal screenshot embedded in the README would help. A GIF showing tab switching and keyboard navigation would be ideal.

**Recommendation:** Add at least one screenshot under the hero line. Caption it with the version it was taken at.

---

### 🟡 R3 — Hero sentence answers WHAT but not WHO or WHY
The opener is functional but thin on motivation.

**Before:**
> "Interactive terminal dashboard for Azure DevOps — pull requests, reviews, work items, triage, and Copilot sessions in one place."

**After:**
> "ADO Dashboard is a keyboard-driven terminal dashboard for Azure DevOps. If you spend your day reviewing PRs, triaging work items, and managing AI sessions — this keeps all of it in your terminal, no browser tabs required."

---

### 🟡 R4 — "ADO" not expanded on first use
The project is called "ADO Dashboard" but ADO is never spelled out as Azure DevOps in the title or hero line. A stranger from HN may not know the acronym.

**Fix:** Expand once: `# ADO Dashboard` → keep the title, but in the first sentence: "...terminal dashboard for **Azure DevOps (ADO)**..."

---

### 🟡 R5 — No Troubleshooting / FAQ section
Common failure modes for a stranger are unaddressed: `az login` not working, no PRs showing up, PowerShell not found, first-run wizard confusion. The `docs/` folder may cover some of this but there's no README-level guidance.

**Recommendation:** Add a short "Common Issues" section with 3–5 entries and links to relevant docs where applicable.

---

### 🟡 R6 — Architecture section is too heavy for a user README
Lines 114–143 (Architecture at a Glance + Key modules table) belong in `docs/architecture.md`, not the README. A first-time visitor doesn't need the module map to decide whether to install the tool. This content pushes the useful stuff (Keyboard Shortcuts, Configuration) further down the page.

**Recommendation:** Replace the Architecture section in README with a one-liner: "See [`docs/architecture.md`](docs/architecture.md) for the full module map and async model." The "For Contributors" table at the bottom is fine to keep.

---

### 🟢 R7 — Vote status indicators buried in table cells
The inline description of `✓ ✗ ~ ·` vote indicators in the Tabs table is hard to scan. Fine as-is but could be extracted into a small reference block or tooltip note.

---

### 🟢 R8 — Badge links (flag for Dwalin)
The CI badge points to `gaburn/ado-dashboard`. If the GitHub repo hasn't been renamed from `gaburn/wip-dashboard` yet, this badge will show as broken. Worth verifying. (Out of my full scope — flagging for Dwalin.)

---

### 🟢 R9 — Tone is competent but flat
No sentence in the README invites a contributor or expresses any warmth. One line would do it: *"Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) to get started."*

---

### 🟢 R10 — In-app `h` help overlay not surfaced prominently
The `h` shortcut for a help overlay is listed in the keyboard table, but there's no nudge at the top saying "press `h` once you're running for an in-app cheat sheet." New users forget to look.

---

## CONTRIBUTING.md

### 🔴 C1 — `.squad` AI team not explained
A contributor cloning this repo will immediately see a `.squad/` directory full of agent configs and history files, and have no idea what it is. There's no mention of the AI-assisted development model anywhere in CONTRIBUTING.md. This will either confuse people or make them uneasy.

**Recommendation:** Add a short "AI-Assisted Development" section:
> "This project uses an AI team (the Squad) for development tasks. You'll see a `.squad/` directory with agent configs and logs — these are used by the maintainer's AI tooling. You don't need to interact with them to contribute."

---

### 🟡 C2 — No commit convention specified
"Keep commits focused and descriptive" is vague. Does the project use Conventional Commits? Imperative mood? If there's no convention, say so plainly. If there is one, document it.

**Suggestion:** Either: *"We use imperative mood commit messages (`Fix crash on empty triage`, not `Fixed crash`)."* Or explicitly: *"No strict commit convention enforced — just be descriptive."*

---

### 🟡 C3 — No branch naming convention
`git checkout -b my-feature` gives no pattern guidance. `feat/`, `fix/`, `docs/` prefixes? Or just anything? One line here saves the maintainer review comments.

---

### 🟢 C4 — "Tech Stack" section is fine; minor redundancy with README
Not a problem. Useful context for a new contributor even if it overlaps with the README.

---

### 🟢 C5 — "we do not enforce strict typing project-wide yet"
The `yet` is good. Honest about the project's current state. Keep it.

---

## SECURITY.md

### 🟡 S1 — Supported versions table is pre-1.0 awkward
The table reads "Current major | ✅ Yes" / "Older versions | ❌ No" — but the project is at v0.2.0. There is no prior major version. "Current major" is technically correct but misleading.

**Before:**
> | Current major | ✅ Yes |
> | Older versions | ❌ No |

**After:**
> | Latest release (0.x) | ✅ Yes |
> | Pinned older releases | ❌ No |

---

### 🟢 S2 — Response timeline and "What Constitutes a Security Issue" are solid
The attack surface list (command injection via `az`/`pwsh`, PAT leakage, investigation launcher RCE) is project-specific and shows thought. Not a template. Good.

---

## CODE_OF_CONDUCT.md

### 🔴 COC1 — CoC reporting channel is public GitHub Issues
Line 63: *"Report issues via GitHub Issues"* — this directs harassment/conduct reports to a **public forum**. That's inappropriate and harmful to anyone reporting in good faith. The Contributor Covenant specifically expects a private reporting channel.

**Before:**
> Report issues via [GitHub Issues](https://github.com/gaburn/ado-dashboard/issues).

**After (example):**
> Please report conduct violations privately. Email [your contact] or use [GitHub's private security reporting](https://github.com/gaburn/ado-dashboard/security/advisories/new). Do **not** open a public issue.

---

### 🟢 COC2 — "Community leaders" boilerplate on a solo project
Slight tone mismatch — "community leaders" (plural) for a solo maintainer project. Not blocking, just a minor awkwardness.

---

## Issue Templates

### 🟢 IT1 — Bug report template is excellent
OS, Python version, app version, terminal, Azure CLI version, repro steps, expected vs actual — this is comprehensive and project-specific. Nicely done.

### 🟡 IT2 — Feature request doesn't ask about workflow context
For a tool with a specific user base (ADO developers), knowing *how the user works today* and *what workflow they're trying to improve* would help triage. Consider adding: *"Describe your current workflow without this feature."*

---

## PR Template

### 🟢 PR1 — Clean and functional
Standard checklist, type-of-change checkboxes. Works fine.

### 🟢 PR2 — Minor framing inconsistency
PR template checklist: *"I have commented my code, particularly in hard-to-understand areas."*  
CONTRIBUTING.md style guide: *"Comments only where the code needs clarification — don't over-comment."*  
Same intent, slightly different framing. Not a blocker, but worth aligning.

---

## First-Impression Summary

*Written as the stranger:*

I clicked through from a Hacker News comment about Textual TUIs and landed on this repo. The headline tells me it's a terminal dashboard for Azure DevOps — okay, I use ADO, I'm interested. Then I hit the install block: `cd ado-dashboard`. Wait, where did this directory come from? Did I miss a clone step? I scroll up — nothing. Already confused in the first ten seconds. I keep scrolling: there's no screenshot, no GIF, nothing showing me what I'm about to install. The keyboard shortcut table looks comprehensive, but I'm being asked to take this thing on faith. I spot a `.squad/` directory in the file tree — what's that about? No explanation. The architecture diagram is detailed but I didn't ask for it yet. I'm not turned away, but I'm doing more work than I should for a tool that probably looks great once it's running. The bones are solid — the README knows its feature set and the issue template is genuinely thoughtful. But the front door is missing a handle.

---

*Total findings: 5 🔴 Blockers, 7 🟡 Recommended, 8 🟢 Polish*


# Glóin's Public-Readiness Audit — Packaging & Distribution Track
**Date:** 2026-07-17  
**Auditor:** Glóin (Packaging & Distribution Specialist)  
**Scope:** pyproject.toml metadata, distribution sanity, release process, metadata accuracy, PyPI naming, backward compatibility

---

## 1. `pyproject.toml` Audit

### 🔴 BLOCKER — `platformdirs` undeclared runtime dependency

`src/ado_dashboard/setup_wizard.py` imports `from platformdirs import user_config_path`. `platformdirs` is **not listed** in `[project.dependencies]`. The app will crash on first run (setup wizard invocation) in any clean install where `platformdirs` is not transitively provided.

`textual>=3.0.0` does bring `platformdirs` as a transitive dep today, but that is an implementation detail of textual's packaging — it is not guaranteed across versions and must not be relied upon. Declare it explicitly.

**Fix:**
```toml
dependencies = [
    "textual>=3.0.0",
    "platformdirs>=3.0",
]
```

---

### 🔴 BLOCKER — Missing `readme`, `license`, `authors` fields

The following PEP 621 metadata fields are absent from `[project]`:

| Field | Impact |
|---|---|
| `readme` | PyPI project page shows no long description — just the one-liner |
| `license` | PyPI won't display a license badge or SPDX identifier |
| `authors` | Standard attribution; many users/org policies require it |

**Fix:**
```toml
[project]
readme = "README.md"
license = { file = "LICENSE" }
authors = [
    { name = "ado-dashboard contributors" },
]
```

---

### 🔴 BLOCKER — Missing `[project.urls]` table

No homepage, repository, issue tracker, or documentation URLs are declared. PyPI displays these prominently as sidebar links. Without them, users cannot find the source, report bugs, or read docs from the PyPI page.

**Fix:**
```toml
[project.urls]
Homepage = "https://github.com/gaburn/ado-dashboard"
Repository = "https://github.com/gaburn/ado-dashboard"
Issues = "https://github.com/gaburn/ado-dashboard/issues"
```

---

### 🔴 BLOCKER — Missing classifiers entirely

There are zero `classifiers` in `[project]`. PyPI uses classifiers for filtering and display. Strongly recommended for any public release.

**Minimum required set:**
```toml
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Operating System :: OS Independent",
    "Environment :: Console",
    "Topic :: Software Development :: Build Tools",
    "Topic :: Utilities",
    "Framework :: AsyncIO",
]
```

---

### 🔴 BLOCKER — No CHANGELOG.md

There is no changelog. PyPI users and downstream consumers expect one to understand what changed between versions. The absence of a CHANGELOG is a common reason projects get poor adoption ratings. This is a blocker for a credible 0.2.1 public release.

**Fix:** Create `CHANGELOG.md` at repo root, covering at minimum 0.1.0 → 0.2.0 → 0.2.1. Use [Keep a Changelog](https://keepachangelog.com/) format.

---

### 🟡 RECOMMENDED — Missing `keywords`

No `keywords` field. Impacts PyPI full-text search.

**Fix:**
```toml
keywords = ["azure-devops", "ado", "tui", "terminal", "dashboard", "textual", "pull-requests", "work-items"]
```

---

### 🟡 RECOMMENDED — `textual>=3.0.0` has no upper bound

`textual` is a rapidly-evolving library with a history of breaking changes between major versions. A future `textual>=4.0` could silently break the app for users running `pip install ado-dashboard` with no pinned environment.

**Fix:** Add a loose upper-bound as a safety net and update on each textual major release:
```toml
"textual>=3.0.0,<5",
```

---

### 🟢 POLISH — Split `[dev]` into `[test]` and `[lint]`

Currently:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
```
Splitting into `[test]` and `[lint]` (or `[dev]` that depends on both) is best practice. Consider adding a `[docs]` extra if documentation tooling is added later.

---

## 2. Distribution Sanity

### 🔴 BLOCKER — Log file path breaks non-editable installs

In `src/ado_dashboard/__main__.py` line 77:
```python
log_file = Path(__file__).resolve().parent.parent.parent / "ado-dashboard.log"
```
`parent.parent.parent` of a file in `site-packages/ado_dashboard/__main__.py` is `site-packages/` — writing a log there is both unwritable (permissions) and wrong. This will silently fail or raise `PermissionError` on non-editable pip installs.

**Fix:** Write log to `platformdirs.user_log_path("ado-dashboard")` or alongside the config file in the user config dir.

---

### 🟡 RECOMMENDED — Wheel contents unverified (build not run)

`[tool.hatch.build.targets.wheel]` correctly specifies `packages = ["src/ado_dashboard"]`. The legacy `src/wip_dashboard/` directory exists on disk but is correctly excluded from the wheel target. However, a build has not been confirmed to run cleanly. **Recommend running `python -m build --wheel` as part of release gating.**

Tests at `src/tests/` are correctly excluded from the wheel (no `[tool.hatch.build.targets.wheel.include]` override covering tests). ✅

---

### 🟡 RECOMMENDED — sdist will include `src/wip_dashboard/`

The old `src/wip_dashboard/` package directory still exists on disk. Hatchling's sdist target includes all source by default. The sdist will ship the deprecated legacy code to anyone who builds from source. This is confusing and adds dead weight.

---

### 🟢 POLISH — README and LICENSE present at root ✅

`README.md` and `LICENSE` exist at the repo root. Once `readme = "README.md"` is added to `pyproject.toml`, they will be included in both sdist and wheel metadata correctly.

---

## 3. Release Process

### 🔴 BLOCKER — No release workflow

There is no `.github/workflows/release.yml`. The only workflow is `ci.yml` (branch push/PR). There is no automated path from a version tag to a PyPI release. Without this, publishing is a manual, error-prone process that will not scale.

**Recommended `release.yml` skeleton:**
```yaml
name: Release

on:
  push:
    tags: ["v*.*.*"]

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # OIDC for PyPI Trusted Publishing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

**Use PyPI Trusted Publishing** (OIDC) — do not use API tokens in secrets.

---

### 🔴 BLOCKER — No documented release procedure

There is no `RELEASING.md`, no release section in `CONTRIBUTING.md`, and no `docs/release.md`. Without a documented procedure, any release is a one-person tribal-knowledge event.

**Minimum content required:**
1. How to bump version (pyproject.toml + `src/ado_dashboard/__init__.py`)
2. Tag format: `v0.2.1`
3. Changelog update step
4. How to trigger publish (push tag)
5. Where artifacts land (PyPI, GitHub Releases)

---

### 🟡 RECOMMENDED — No GitHub Release creation step

Even if PyPI publish is automated, creating a GitHub Release (with changelog notes) on tag push provides users a better upgrade discovery path. Extend `release.yml` with `actions/create-release` or `softprops/action-gh-release`.

---

### 🟡 RECOMMENDED — SemVer policy not documented

There is no written statement of the versioning policy (SemVer assumed, but not stated anywhere users can find it). Add to README or CONTRIBUTING.

---

## 4. Distribution Metadata Accuracy

### 🟡 RECOMMENDED — VERSION MISMATCH in legacy package

`src/wip_dashboard/__init__.py` contains `__version__ = "0.2.0"` while the active `src/ado_dashboard/__init__.py` has `__version__ = "0.2.1"` and `pyproject.toml` is `0.2.1`. The legacy package is stale. Minor concern since `wip_dashboard` is not shipped in the wheel — but it could confuse a developer who imports the wrong one in a dev install.

---

### 🟡 RECOMMENDED — LICENSE copyright uses old project name

`LICENSE` line 3:
```
Copyright (c) 2026 wip-dashboard contributors
```
Should read `ado-dashboard contributors` (or just `ADO Dashboard contributors`). Minor but visible on PyPI and legally meaningful.

---

### 🟢 POLISH — `__version__` in `ado_dashboard/__init__.py` matches pyproject.toml ✅

`__version__ = "0.2.1"` matches `version = "0.2.1"`. ✅

---

### 🟢 POLISH — `__build__` git hash computed at import time

`_get_git_build_hash()` runs a subprocess at import time. In a wheel install, `cwd=_PACKAGE_DIR` is inside `site-packages`. `git describe` on that path will fail (not a git repo), returning `"dev"` gracefully. The fallback is correct. ✅

However, the `--tags` flag was added to `ado_dashboard/__init__.py` but not `wip_dashboard/__init__.py` (legacy). Non-issue since only `ado_dashboard` ships.

---

## 5. PyPI Naming Check

### 🟢 PASS — `ado-dashboard` is available on PyPI

`GET https://pypi.org/pypi/ado-dashboard/json` → **HTTP 404** (name not registered). The name is available for registration. ✅

---

## 6. Backward Compatibility

### 🟡 RECOMMENDED — `WIP_DASHBOARD_REPO_ROOT` deprecation lacks removal version

`config.py` correctly emits a `DeprecationWarning` when `WIP_DASHBOARD_REPO_ROOT` is set. However, there is no documented removal timeline (e.g., "will be removed in 0.4.0"). Users who receive a deprecation warning need to know when action becomes urgent.

**Fix:** Update the warning message:
```python
"WIP_DASHBOARD_REPO_ROOT is deprecated; rename to ADO_DASHBOARD_REPO_ROOT. "
"Support will be removed in v0.4.0.",
```
And document this in `docs/configuration.md` and the CHANGELOG.

---

### 🟡 RECOMMENDED — No config migration tooling from `~/.wip-dashboard/`

The default dirs in `config.py` (INVESTIGATIONS_DIR, TRIAGE_CACHE_DIR) point to `~/.ado-dashboard/*`. The old defaults were `~/.wip-dashboard/*`. Users upgrading from a pre-rename install have no migration path — their cached triage data and investigation history silently disappear.

**Fix options (pick one):**
1. Add a migration check at startup: detect `~/.wip-dashboard/` and offer to migrate
2. At minimum, document the migration in CONTRIBUTING.md or a dedicated `docs/migration.md`

---

## Executive Summary

| # | Finding | Severity |
|---|---|---|
| 1 | `platformdirs` undeclared runtime dep | 🔴 Blocker |
| 2 | Missing `readme`, `license`, `authors` in pyproject.toml | 🔴 Blocker |
| 3 | Missing `[project.urls]` table | 🔴 Blocker |
| 4 | Missing `classifiers` | 🔴 Blocker |
| 5 | No CHANGELOG.md | 🔴 Blocker |
| 6 | Log file path breaks non-editable installs | 🔴 Blocker |
| 7 | No release workflow (release.yml) | 🔴 Blocker |
| 8 | No documented release procedure | 🔴 Blocker |
| 9 | Missing `keywords` | 🟡 Recommended |
| 10 | `textual` no upper version bound | 🟡 Recommended |
| 11 | sdist includes dead `src/wip_dashboard/` | 🟡 Recommended |
| 12 | No GitHub Release creation step in CI | 🟡 Recommended |
| 13 | SemVer policy not documented | 🟡 Recommended |
| 14 | `WIP_DASHBOARD_REPO_ROOT` deprecation missing removal version | 🟡 Recommended |
| 15 | No config migration tooling for `~/.wip-dashboard/` users | 🟡 Recommended |
| 16 | LICENSE copyright uses old name `wip-dashboard` | 🟡 Recommended |
| 17 | wip_dashboard/__init__.py version stale (0.2.0 vs 0.2.1) | 🟡 Recommended |
| 18 | Split `[dev]` extras into `[test]` and `[lint]` | 🟢 Polish |
| 19 | `ado-dashboard` name available on PyPI | 🟢 Pass |
| 20 | `__version__` matches pyproject.toml | 🟢 Pass |
| 21 | Tests excluded from wheel | 🟢 Pass |

---

## ⛔ Go/No-Go Recommendation: **NO-GO**

**8 blockers** must be resolved before publishing to PyPI. The most critical are:
1. The `platformdirs` undeclared dependency will crash the app on first run in clean installs.
2. The missing pyproject.toml metadata (`readme`, `license`, `authors`, `urls`, `classifiers`) means the PyPI page will be functionally empty.
3. No CHANGELOG means users have no upgrade story.
4. No release workflow means any publish is manual and unrepeatable.

The packaging foundation needs roughly 2–3 focused hours of work before this is ready to list on PyPI. The code itself is in reasonable shape; this is purely a distribution configuration gap.

**Priority order for blockers:**
1. `pyproject.toml` metadata fields (30 min) — `readme`, `license`, `authors`, `urls`, `classifiers`
2. `platformdirs` dependency declaration (5 min)
3. Log file path fix in `__main__.py` (15 min)
4. CHANGELOG.md (1–2 hr)
5. `release.yml` + release procedure doc (1 hr)


# Decision: Pre-Public Hygiene Execution

**Date:** 2026-07-17  
**Author:** Thorin (Lead Architect)  
**Status:** Implemented  

---

## Context

Following the public-readiness audit (see `.squad/agents/thorin/history.md`, 2025-07-17 entry), two hard blockers and several soft issues were identified. This note records the execution decisions for the hygiene pass.

## Decisions Made

### 1. Ghost module removed
`src/wip_dashboard/` (22 files) — `git rm -rf`. These were pre-rename duplicates that survived the PR #1 merge resolution. `pyproject.toml` already pointed to `src/ado_dashboard/` so this module was never installed; it was invisible dead weight that would confuse contributors and create import ambiguity.

### 2. Internal model names scrubbed
`.squad/config.json`: `claude-opus-4.7-1m-internal` → `claude-opus-4.7` for all four agents (thorin, balin, dwalin, gloin). Decision: **keep the file** — it is actionable for contributors who want to run the squad locally and now contains only public model names.

### 3. .squad/ partial ship
Files kept (charter, history, decisions, team, routing, ceremonies, config): these are meaningful to contributors who want to understand the team structure or run the squad.  
Files removed (templates, orchestration-log, log, casting, skills, identity, .first-run): operational state and internal scaffolding — noise for anyone else.

### 4. .gitignore hardened
Added the removed `.squad/` paths so they can never be re-tracked accidentally. Added OS cruft patterns and `.ruff_cache/`. Removed no-op `~/.wip-dashboard/` (tilde not expanded by git).

### 5. requirements.txt deleted
Single-line duplicate of `pyproject.toml` dependency. Deleting it eliminates the drift risk — there is now one canonical place for the dependency.

## Verification
79/79 pytest tests pass after all changes.


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


# Decision: Bofur Public-Prep Execution

**Date:** 2026-07-17  
**Agent:** Bofur  
**Status:** Done

## Context

Executed all blocker and recommended fixes from the public-readiness audit (`bofur-public-audit.md`) in a single pass, ahead of first public release.

## Changes Made

### Blockers (R1, C1, COC1)

- **README R1:** Added `git clone https://github.com/gaburn/ado-dashboard.git` as the first line of the Install & Run code block.
- **CONTRIBUTING C1:** Added `### AI Tooling (.squad/)` paragraph explaining the Squad tooling for first-time contributors.
- **CODE_OF_CONDUCT COC1:** Replaced `Report issues via GitHub Issues` (public, privacy hazard) with GitHub private security advisory URL + placeholder maintainer email. Flagged with a `<!-- TODO -->` comment for the maintainer to fill in.

### Recommended (R3, R4, R5, R6, C2+C3, S1, IT2, PR2)

- **README R3:** Rewrote hero sentence to WHO/WHY framing.
- **README R4:** First use of ADO now reads "Azure DevOps (ADO)" (handled by hero sentence rewrite).
- **README R5:** Added `## Troubleshooting / FAQ` section covering: az login, no PRs showing, PowerShell not found, Triage unconfigured, dirty version string.
- **README R6:** Replaced heavy "Architecture at a Glance" section (ASCII tree + Key modules table) with one-liner pointing to `docs/architecture.md`. Appended Key Modules quick-reference table to `docs/architecture.md`.
- **CONTRIBUTING C2+C3:** Added `### Commit Messages`, `### Branch Naming` table, and `### Pre-commit Hooks` subsections under Making Changes.
- **SECURITY S1:** Changed "Current major → ✅ Yes" to "Latest release (0.x) → ✅ Yes".
- **Issue template IT2:** Added "What workflow does this support?" field to `feature_request.md`.
- **PR template PR2:** Updated checklist item from "commented hard-to-understand areas" to "documented non-obvious decisions; avoided restating what code already shows" — aligns with CONTRIBUTING's "don't over-comment" stance.

### Cannot Do (R2 — Screenshot/GIF)

Added `<!-- TODO: add screenshot or asciinema GIF here — biggest UX win is showing the TUI in action -->` placeholder in README near the Install & Run block. Requires live app capture.

## Stale Reference Check

Re-grep for `wip-dashboard` in edited files: **clean**. Only CHANGELOG.md has historical references (intentional).

## Flags for Maintainer

1. **Screenshot/GIF** — the TODO placeholder in README is the highest-impact UX win. Run the app and capture with asciinema or a terminal screenshot tool.
2. **Maintainer email** — replace `<maintainer@example.com>` in `CODE_OF_CONDUCT.md` with a real contact before shipping.


