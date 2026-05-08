# Configuration

Settings are resolved in strict priority order:

```
CLI args  >  environment variables  >  config file  >  built-in defaults
```

---

## Layer 1 — CLI Arguments (highest priority)

Processed in `__main__._parse_args` and applied via `config.apply_overrides(args)`.

| Flag | `config` attribute | Example |
|---|---|---|
| `--org <url>` | `ORG_URL` | `--org https://dev.azure.com/myorg` |
| `--project <name>` | `PROJECT` | `--project MyProject` |
| `--projects <list>` | `PROJECTS` | `--projects Proj1,Proj2` |
| `--user <email>` | `USER_EMAIL` | `--user me@example.com` |
| `--setup` | _(triggers wizard)_ | |

`apply_overrides` only overwrites when the value is not `None`.

---

## Layer 2 — Environment Variables

Read at module import time (`os.environ.get`). `config.load_from_file` skips a config-file key when the corresponding env var is already set.

| Variable | `config` attribute | Default |
|---|---|---|
| `ADO_ORG_URL` | `ORG_URL` | `""` |
| `ADO_PROJECT` | `PROJECT` | `""` |
| `ADO_USER_EMAIL` | `USER_EMAIL` | `""` |
| `TRIAGE_SCRIPT_PATH` | `TRIAGE_SCRIPT_PATH` | `""` (must be configured) |
| `TRIAGE_BOARD` | `TRIAGE_BOARD` | First board option URL |
| `INVESTIGATIONS_DIR` | `INVESTIGATIONS_DIR` | `~/.wip-dashboard/investigations` |
| `INVESTIGATION_MODEL` | `INVESTIGATION_MODEL` | `""` (launcher default) |
| `INVESTIGATION_AGENT` | `INVESTIGATION_AGENT` | `""` |
| `AI_TRIAGE_MODE` | `AI_TRIAGE_MODE` | `copilot` |
| `TRIAGE_CACHE_DIR` | `TRIAGE_CACHE_DIR` | `~/.wip-dashboard/triage` |
| `TRIAGE_CACHE_MAX_AGE` | `TRIAGE_CACHE_MAX_AGE_SECONDS` | `1800` |
| `COPILOT_SESSION_DIR` | `COPILOT_SESSION_DIR` | `~/.copilot/session-state` |
| `SESSION_MAX_AGE_DAYS` | `SESSION_MAX_AGE_DAYS` | `7` |
| `WIP_DASHBOARD_REPO_ROOT` | `REPO_ROOT` | git-root auto-detected |
| `BAND_REPO_ROOT` | `REPO_ROOT` | _(deprecated alias for `WIP_DASHBOARD_REPO_ROOT`)_ |

**Note:** `PROJECTS` (the list used for PR queries) has no corresponding env var — it can only be set via config file, CLI `--projects`, or the in-app Settings screen.

---

## Layer 3 — Config File

**Location (platform-dependent):**

| Platform | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\wip-dashboard\config.json` |
| macOS | `~/Library/Application Support/wip-dashboard/config.json` |
| Linux | `~/.config/wip-dashboard/config.json` |

Determined by `platformdirs.user_config_path("wip-dashboard")`.

### Config File Schema

```json
{
  "_config_version": 1,
  "ado_org_url": "https://dev.azure.com/<your-org>",
  "ado_projects": ["MyProject"],
  "ado_project": "MyProject",
  "user_email": "me@example.com",
  "copilot_session_dir": "~/.copilot/session-state",
  "session_max_age_days": 7,

  // --- Optional (not written by the setup wizard; set in-app or manually) ---
  "triage_script_path": "/path/to/Get-TriageItems.ps1",
  "triage_board": "https://dev.azure.com/<your-org>/<your-project>/_backlogs/...",
  "triage_board_options": [
    ["My Team Board", "https://dev.azure.com/<your-org>/<your-project>/_backlogs/..."]
  ],
  "triage_pr_repo": "<your-repo-name>",
  "investigations_dir": "~/.wip-dashboard/investigations",
  "investigation_model": "",
  "investigation_agent": "",
  "ai_triage_mode": "copilot",
  "triage_cache_dir": "~/.wip-dashboard/triage",
  "triage_cache_max_age_seconds": 1800
}
```

`load_from_file` iterates each key and sets the corresponding `config` module global **only** when the matching env var is absent. `ado_projects` and `triage_board_options` are always taken from the file (no env var guards them).

---

## Layer 4 — Built-in Defaults

Module-level constants in `config.py` (`_DEFAULT_ORG_URL = ""`, etc.). The application will run with empty strings for org/user if no other layer provides them — queries will fail with informative `ADOClientError` messages.

---

## Setup Wizard

Run automatically on first launch (no config file) or explicitly with `wip-dashboard --setup`.

The wizard collects:

1. ADO organization URL
2. Projects for PR queries (comma-separated)
3. Project for work items (defaults to first PR project)
4. User email (auto-detected via `az account show` when possible)
5. Copilot session directory
6. Session max age (days)

Triage and investigation settings are **not** collected by the wizard — configure them via the in-app **Settings** screen (`s`) or environment variables.

The wizard skips automatically in non-interactive environments (`sys.stdin.isatty() == False`).

---

## In-App Settings Screen

Press `s` to open Settings. Changes are saved to the config file via `setup_wizard.save_config` and applied to `config` module globals immediately.

The Settings screen also provides:

- **Triage Boards** — dynamic add/remove rows of `(name, URL)` pairs; stored as `triage_board_options` in the config file.
- **Investigation Model** — populated at runtime from `discover_models()` on the active `InvestigationLauncher` (see `docs/investigation.md`), or `[]` when no backend is configured.
- **Investigation Agent** — populated from personal (`~/.copilot/agents`, `~/.claude/agents`) and repo-level (`.github/agents`, `.claude/agents`) directories via the active launcher.

---

## Concrete Examples

```bash
# First-time setup
wip-dashboard --setup

# Override org and user without touching the config file
ADO_ORG_URL=https://dev.azure.com/<your-org> ADO_USER_EMAIL=me@example.com wip-dashboard

# One-shot: different projects
wip-dashboard --projects ProjectA,ProjectB --org https://dev.azure.com/<your-org>

# Disable AI triage
AI_TRIAGE_MODE=off wip-dashboard
```
