# Squad Decisions

## Active Decisions

### Decision: Env var rename WIP_DASHBOARD_REPO_ROOT → ADO_DASHBOARD_REPO_ROOT

**Date:** 2026-07-17  
**Author:** Thorin (lead architect)

#### Context

App was renamed `wip-dashboard` → `ado-dashboard`. Env var names that carry
the old `WIP_DASHBOARD` prefix were queued for a follow-up pass. This is that
pass for `WIP_DASHBOARD_REPO_ROOT`.

Note: `config.py` had an intermediate stale name (`ado_dashboard_REPO_ROOT`,
lowercase) left from the prior rename. That was corrected to the canonical
uppercase `ADO_DASHBOARD_REPO_ROOT` in the same commit.

#### Decision

**Canonical name:** `ADO_DASHBOARD_REPO_ROOT`

**Backward compat:** Implemented. `WIP_DASHBOARD_REPO_ROOT` is still read as a
deprecated fallback (`warnings.warn(DeprecationWarning)`). Cost: ~10 lines in
`config.py`. Benefit: existing user shells/CI configs keep working; they see a
clear deprecation message on first run.

#### Files changed

| File | Change |
|------|--------|
| `src/ado_dashboard/config.py` | Primary var → `ADO_DASHBOARD_REPO_ROOT`; fallback reads `WIP_DASHBOARD_REPO_ROOT` with DeprecationWarning |
| `README.md` | Table row updated |
| `docs/configuration.md` | Table row updated |

#### User action required

If you have `WIP_DASHBOARD_REPO_ROOT` set in your shell profile or CI, rename
it to `ADO_DASHBOARD_REPO_ROOT`. The old name continues to work but logs a
`DeprecationWarning`.

---

### Decision: Docs Structure Convention for wip-dashboard

**Author:** Thorin  
**Date:** 2026-05-08  
**Status:** Proposed

#### Context

The project had no contributor or architecture documentation. A docs pass was needed to capture the architecture before the codebase grows further.

#### Decision

Create a `docs/` directory at the repo root with these five documents, each tightly scoped:

| File | Scope |
|---|---|
| `docs/architecture.md` | Module map, Mermaid diagram, async model, screen lifecycle, state map |
| `docs/ado-integration.md` | `az` CLI shapes, auth, error handling, JSON mapping |
| `docs/triage-and-investigation.md` | PS1 script contract, categorizer pipeline, AI enrichment, investigation launcher |
| `docs/configuration.md` | 4-layer resolution, full schema, setup wizard, in-app settings |
| `docs/development.md` | Onboarding, tests, adding tabs/settings, CSS conventions, known cruft |

The `README.md` retains user-facing content and gains an "Architecture at a glance" module summary + "For contributors" table linking into `docs/`.

#### Rationale

- Separation of concerns: user docs in README, contributor/architecture docs in `docs/`.
- Each doc has a single axis — no doc tries to cover both "how to configure" and "how to hack on".
- Mermaid diagrams in fenced code blocks; no external tooling required.
- `docs/development.md` is the "living cruft tracker" — known scratch files are noted there so they are visible but not deleted prematurely.

#### Consequences

- Future architecture decisions should be documented in `docs/architecture.md` (or a new ADR under `docs/adr/` if the team adopts ADR format).
- The `docs/` directory is not part of the wheel build and is purely for contributors.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
