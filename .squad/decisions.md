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

### Decision: Triage empty-state must branch on configured vs. unconfigured

**Date:** 2026-05-28  
**Author:** Bofur  
**Status:** Implemented

#### Rule

**Never reuse one signal for two different states.**  
An empty list because nothing was configured looks different from an empty list because everything's done.

#### Context

The Triage tab showed `"No items in triage queue 🎉"` in ALL empty cases, including when
`triage_script_path` was never set. The 🎉 implies "all done!" — which is actively wrong
when the user hasn't opted in to Triage at all.

Separately, on every app launch, a warning toast fired:
> `"Triage: triage_script_path is not configured — copy Get-TriageItems.ps1.example…"`

Triage is optional. Scolding users for not setting up a feature they didn't ask for is noise.

#### Decisions

##### 1. Notification suppression
`_fetch_and_populate_triage()` and `_refresh_triage()` in `dashboard.py` now check
`config.TRIAGE_SCRIPT_PATH` **before** calling `fetch_triage_items()`. When the path
is empty, the fetch is skipped silently (INFO log only) and the unconfigured empty state
is shown. The `notify()` warning path is preserved for real errors (script set but fails).

##### 2. Empty-state branching
`_populate_triage_groups()` branches on `config.TRIAGE_SCRIPT_PATH`:

| Condition | Message |
|-----------|---------|
| `TRIAGE_SCRIPT_PATH` falsy | "No triage board configured. Add one in Settings if you'd like to use Triage." |
| `TRIAGE_SCRIPT_PATH` set, results empty | "No items in triage queue 🎉" |

##### 3. Docs reference preserved in Settings
The helpful `docs/triage-and-investigation.md` reference was removed from the toast (noise
when unconfigured). It now appears as a static hint in the Triage Boards section of the
Settings screen (`settings.py`) — visible only when the user is actively trying to configure
triage. The reference also remains in the `TriageClientError` raised when the path IS set but
the script file is missing (actionable error, correct context).

##### 4. Settings discoverability
The global `s` key binding for Settings is already in the footer (`Binding("s", "open_settings", "Settings")`).
No additional binding was added. The empty-state message mentions "Settings" to connect the
user to the fix.

#### Pattern to follow

For any future "feature not configured" empty state:
1. **Do not notify at startup** — notification implies urgency or failure.
2. **Use the tab/panel itself** as the invitation to configure.
3. **Name the cause** (not configured), **point to the fix** (Settings), **be optional in tone** (if you'd like).
4. **Keep the configured-but-empty copy** as a distinct, accurate message.

---

### Decision: Normalize ADO org URL on input

**Date:** 2026-05-27  
**Author:** Balin  
**Status:** Implemented

#### Context

After the `wip-dashboard` → `ado-dashboard` rename + reinstall, the setup wizard
accepted a bare org name (e.g. `"microsoft"`) when prompting for the organization
URL. The value was saved verbatim to the config file. When the app later passed it
to `az` as `--org microsoft`, the CLI rejected it:

```
ERROR: --organization must be specified. The value should be the URI of your
Azure DevOps organization, for example: https://dev.azure.com/MyOrganization/
```

This was **not** a regression in the `az` invocation code — `ado_client.py` was
already threading `config.ORG_URL` through every `--org` flag correctly.

#### Root Cause

The setup wizard (and the config loading layer) had no validation or normalization
for `ado_org_url`. A user entering just `"microsoft"` got a broken config.

Secondary issue: the `ado_project` field (single-project for work-item queries)
contained the full comma-separated project list — the user pasted the multi-project
value into that prompt too.

#### Decision

**Add `_normalize_org_url()` as a defensive normalization function in `config.py`.**

Rules:
- Strip surrounding whitespace and trailing `/`
- If the value doesn't start with `http://` or `https://`, prepend `https://dev.azure.com/`
- Empty string passes through unchanged (missing config is handled elsewhere)

Apply normalization at **two points**:
1. `config.load_from_file()` — when reading from disk
2. `config.apply_overrides()` — when `--org` CLI flag is passed

Additionally, add **inline normalization in `setup_wizard.py`** immediately after
the org URL prompt, before the value is written to disk. This ensures the config
file itself is clean, not just the in-memory value.

#### Actions Taken

- Added `_normalize_org_url()` to `config.py`
- Applied it in `load_from_file()` and `apply_overrides()`
- Added inline normalization in `setup_wizard.run_setup()`
- Repaired the live config at `%LOCALAPPDATA%\ado-dashboard\ado-dashboard\config.json`:
  - `ado_org_url`: `"microsoft"` → `"https://dev.azure.com/microsoft"`
  - `ado_project`: `"Windows Defender, DefenderCommon, OS, WDATP"` → `"Windows Defender"`
- All 79 existing tests pass

#### Out of Scope / Flagged

- Wizard banner still reads "WIP Dashboard — First-Run Setup" (pre-rename copy).
  Flagged to **Bofur** (UX copy owner) for rename to "ADO Dashboard".
- No migration utility was added for users who have a `~/.wip-dashboard/` config.
  Old config location: `%LOCALAPPDATA%\wip-dashboard\wip-dashboard\config.json`.
  User action: run `ado-dashboard --setup` to repopulate the new config.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
