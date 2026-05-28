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
