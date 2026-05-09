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

