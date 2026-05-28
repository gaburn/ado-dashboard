# Issue #3 Architecture Review — Thorin

**Date:** 2026-05-28  
**Author:** Thorin (Lead Architect)  
**Agent Model:** claude-opus-4.7  
**Duration:** ~4 minutes

## Summary

Thorin completed architecture design for EditWorkItemScreen (track #3-b). Locked decisions on screen structure, widget composition, async save worker with concurrency handling, error translation, and 12-point acceptance gate. Design coordinates with Balin's API layer (#3-a), Bofur's UX spec, and Dwalin's test plan.

## Blocking Finding

**`WorkItem` dataclass is missing `rev: int | None` field.** Required for concurrency control. Balin must add in track #3-a before screen track #3-b starts.

## Decisions

- Full Screen[bool | None], not modal
- Launch binding: `e` on DetailScreen (WorkItems only)
- Dirty tracking: reactive state, subtitle suffix `" *"`
- Save worker: `@work(exclusive=True)` with guarded refetch
- Conflict resolution: user modal, no auto-merge
- Five v1 fields: Title, State, Iteration, Area, Description
- Type read-only (deferred to #3-f)
- Error translation at screen boundary
- Demo mode: disabled

## Coordination

- **Balin:** Add `rev` field (BLOCKING)
- **Bofur:** Confirm Iteration/Area flat vs. tree; own CSS
- **Dwalin:** Add 4 rev-conflict modal test cases

## Status

✅ Design complete. Awaiting team sign-off and `rev` field addition.
