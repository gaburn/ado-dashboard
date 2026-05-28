# Session Log: Triage Unconfigured-State UX Fix

**Session ID:** 2026-05-28T00-44-55Z-triage-empty-state  
**Date:** 2026-05-28T00:44:55Z  
**Requested by:** Copilot  
**Agent:** Scribe (documentation & decisions)

## Session Context

Bofur completed work on the Triage tab UX to properly distinguish between "unconfigured" and "configured but empty" states. The issue was that the app scolded users for not setting up an optional feature.

## Decisions Archived

- **Decision:** Triage empty-state must branch on configured vs. unconfigured
  - Notification suppression: silent when `triage_script_path` is unset
  - Empty-state branching: distinct copy for unconfigured vs. empty queue
  - Docs reference moved to Settings (actionable context)
  - Pattern: Do not notify at startup; use the UI as the invitation to configure

## Files Modified

- `src/ado_dashboard/screens/dashboard.py`
- `src/ado_dashboard/screens/settings.py`

## Test Results

All 79 tests pass.

## Pattern to Remember

For any future "feature not configured" empty state:
1. Do not notify at startup (implies urgency or failure)
2. Use the tab/panel itself as the invitation to configure
3. Name the cause, point to the fix (Settings), be optional in tone
4. Keep the configured-but-empty copy as a distinct, accurate message
