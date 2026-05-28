# Thorin Architecture Review Run — Issue #3 Screen

**Date:** 2026-05-28  
**Timestamp:** 2026-05-28T16:36:42Z  
**Agent:** Thorin (Lead Architect, claude-opus-4.7)  
**Duration:** ~4 minutes  
**Task:** Architecture design for EditWorkItemScreen (track #3-b) and design review of API layer (track #3-a) dependency

## Run Summary

Thorin completed comprehensive architecture design for Issue #3 edit work-item screen implementation. Reviewed and confirmed API design from Balin, UX spec from Bofur, and test plan from Dwalin. Locked down screen structure, widget composition, async save worker, concurrency handling, error translation, and acceptance gate.

## Key Finding — BLOCKING DEPENDENCY

**CRITICAL:** `WorkItem` dataclass is **missing `rev: int | None` field**. This field is required for concurrency control (client-side rev refetch before write). Balin's API design in track #3-a assumes this field exists but it does **not** in the current model (models.py:311–383).

**Resolution:** Balin must add `rev: int | None = None` to `WorkItem` in track #3-a, populate from `data.get("rev")` in `from_az_json()`. Screen track #3-b cannot start without this field.

## Decisions Locked

- Screen type: full `Screen[bool | None]`, not modal (accommodates tall form)
- Launch binding: `e` on DetailScreen for WorkItems only (unused keystroke)
- Widgets: Input, Select, TextArea backed by reactive dirty state
- Save worker: `@work(exclusive=True)` with guarded refetch on concurrency conflict
- Conflict resolution: user modal (Refresh & merge / Discard / Overwrite), no auto-merge
- Error translation: screen is single translation point; all Balin exceptions mapped to UI affordances
- Demo mode: EditWorkItemScreen disabled (DemoAdoClient has no write surface)
- v1 fields: Title, State, Iteration, Area, Description (Type read-only for #3-f)

## Coordination Notes

- **Balin:** Must add `rev` field to `WorkItem` before track #3-b starts (blocking)
- **Bofur:** Confirm flat vs. tree for Iteration/Area selectors; own CSS for new selectors
- **Dwalin:** Add ~4 test cases for rev-conflict modal paths (Refresh, Discard, double-change)

## Document Archived

- Input file: `.squad/decisions/inbox/thorin-issue-3-screen-architecture.md`
- Output file: `.squad/decisions.md` (section added)

## Status

✅ Design complete, ready for team sign-off on open questions. Blocked on Balin adding `rev` field.
