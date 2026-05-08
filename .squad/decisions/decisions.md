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
