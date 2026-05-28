# Decision: Normalize ADO org URL on input

**Date:** 2026-05-27  
**Author:** Balin  
**Status:** Implemented

## Context

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

## Root Cause

The setup wizard (and the config loading layer) had no validation or normalization
for `ado_org_url`. A user entering just `"microsoft"` got a broken config.

Secondary issue: the `ado_project` field (single-project for work-item queries)
contained the full comma-separated project list — the user pasted the multi-project
value into that prompt too.

## Decision

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

## Actions Taken

- Added `_normalize_org_url()` to `config.py`
- Applied it in `load_from_file()` and `apply_overrides()`
- Added inline normalization in `setup_wizard.run_setup()`
- Repaired the live config at `%LOCALAPPDATA%\ado-dashboard\ado-dashboard\config.json`:
  - `ado_org_url`: `"microsoft"` → `"https://dev.azure.com/microsoft"`
  - `ado_project`: `"Windows Defender, DefenderCommon, OS, WDATP"` → `"Windows Defender"`
- All 79 existing tests pass

## Out of Scope / Flagged

- Wizard banner still reads "WIP Dashboard — First-Run Setup" (pre-rename copy).
  Flagged to **Bofur** (UX copy owner) for rename to "ADO Dashboard".
- No migration utility was added for users who have a `~/.wip-dashboard/` config.
  Old config location: `%LOCALAPPDATA%\wip-dashboard\wip-dashboard\config.json`.
  User action: run `ado-dashboard --setup` to repopulate the new config.
