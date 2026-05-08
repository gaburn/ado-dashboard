# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| TUI architecture, async loop, widgets, theming | Thorin | App shell, screens, workers, reactive state, Textual CSS |
| Azure DevOps integration | Balin | Work item queries (WIQL), PR lists, PAT auth, pagination, retries |
| Testing | Dwalin | pytest, Textual Pilot, snapshot tests, ADO mocks, CI |
| Terminal UX & accessibility | Bofur | Key maps, info density, color/contrast, copy, empty/loading states |
| Packaging & distribution | Glóin | pyproject.toml, entry points, pipx, config schema, secrets/PAT loading |
| Code review (architecture) | Thorin | Final architectural sign-off, async/worker contracts |
| Code review (API correctness) | Balin | ADO endpoint usage, pagination, retry behavior |
| Code review (tests) | Dwalin | Coverage gates, fixture hygiene, flaky-test triage |
| Scope & priorities | Thorin | What ships next, trade-offs, breaking changes |
| Session logging | Scribe | Automatic — never needs routing |
| Work-queue monitoring | Ralph | Issue/PR scan, triage prompts, idle-watch |

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Lead |
| `squad:{name}` | Pick up issue and complete the work | Named member |

### How Issue Assignment Works

1. When a GitHub issue gets the `squad` label, **Thorin** (Lead) triages it — analyzing content, assigning the right `squad:{member}` label, and commenting with triage notes.
2. When a `squad:{member}` label is applied, that member picks up the issue in their next session.
3. Members can reassign by removing their label and adding another member's label.
4. The `squad` label is the "inbox" — untriaged issues waiting for Lead review.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn the tester to write test cases from requirements simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. The Lead handles all `squad` (base label) triage.
