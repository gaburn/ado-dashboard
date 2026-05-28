# ADO Dashboard

Interactive terminal dashboard for Azure DevOps — pull requests, reviews, work items, triage, and Copilot sessions in one place.

[![CI](https://github.com/gaburn/wip-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/gaburn/wip-dashboard/actions/workflows/ci.yml)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Install & Run

```bash
cd wip-dashboard
pip install -e .
ado-dashboard
```

On first launch an interactive setup wizard walks you through configuration.
Re-run it any time with `ado-dashboard --setup`.

## Prerequisites

| Requirement | Install / verify |
|---|---|
| **Python 3.12+** | `python --version` |
| **Azure CLI** (authenticated) | [Install](https://learn.microsoft.com/cli/azure/install-azure-cli), then `az login` |
| **azure-devops extension** | `az extension add --name azure-devops` |
| **Triage only:** PowerShell (`pwsh` or `powershell`) | A `Get-TriageItems.ps1.example` template is included; copy and customise it, then set `triage_script_path` in Settings |

## Tabs

| # | Tab | What it shows |
|---|---|---|
| 1 | **My PRs** | Active PRs you created (across multiple projects). Draft PRs are dimmed. Status column shows colored approval indicators: ✓ green (approved), ✗ red (rejected), ~ yellow (suggestions), · dim (no votes). |
| 2 | **Reviewing** | PRs where you are a reviewer. Vote status shown as ✓ approved / ✗ rejected / · pending. Declined PRs filtered out. Approved reviews highlighted green. |
| 3 | **Work Items** | ADO work items assigned to you. Filters out Closed, Done, Completed, Cut, and Resolved states. |
| 4 | **Triage** | On-call triage board with a board selector dropdown, priority groups, categorization, action plan, and clickable links. Switching boards refreshes the view with a loading indicator. |
| 5 | **Copilot Sessions** | Active Copilot CLI sessions with status, intent, and working directory. Press `R` (Shift+R) to resume an inactive session in a new Windows Terminal tab. Press `f` to focus the terminal of an active session. |

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `↑` `↓` | Move between rows |
| `Enter` | Open detail view |
| `Escape` | Back to list / clear search |
| `1`–`5` | Switch tab |
| `o` | Open selected item in browser |
| `c` | Copy selected item to clipboard |
| `r` | Refresh data |
| `/` | Search / filter active tab |
| `SHIFT`+`0`–`6` | Sort by column |
| `R` (Shift+R) | Resume a Copilot session in new terminal tab |
| `f` | Focus terminal of active session |
| `s` | Settings screen |
| `i` | Investigate selected triage item (launches Copilot session) |
| `I` (Shift+I) | Investigate entire triage board |
| `h` | Help overlay |
| `q` | Quit |

## Configuration

Settings are resolved in order: **CLI args → environment variables → config file → defaults**.

Config file location: `%LOCALAPPDATA%\ado-dashboard\config.json` (Windows) or `~/.config/ado-dashboard/config.json` (Linux/macOS).

| Method | Example |
|---|---|
| Setup wizard | `ado-dashboard` (first run) or `ado-dashboard --setup` |
| CLI flag | `--projects MyProject,OtherProject` |
| In-app | Press `s` to open settings |

### CLI Flags

| Flag | Description |
|---|---|
| `--setup` | Re-run the configuration wizard |
| `--org` | Azure DevOps organization URL |
| `--projects` | Comma-separated project list for PR queries |
| `--user` | User email for ADO queries |

### Environment Variables

| Variable | Maps to |
|---|---|
| `ADO_ORG_URL` | Organization URL |
| `ADO_PROJECT` | Default project |
| `ADO_USER_EMAIL` | User email |
| `TRIAGE_BOARD` | Default triage board URL |
| `INVESTIGATION_MODEL` | Model for investigation sessions |
| `INVESTIGATION_AGENT` | Agent for investigation sessions |
| `INVESTIGATIONS_DIR` | Directory for investigation results |
| `ADO_DASHBOARD_REPO_ROOT` | Repository root (for skill discovery) |

In **Settings** (`s`), the **Triage Boards** section lets you configure multiple boards with separate **Name** and **URL** fields, then add/remove entries dynamically. Boards are stored in `config.json` as `[display_name, url]` pairs.

## UI Details

- **Status bar** — global counts per tab plus triage priority breakdown.
- **Dark theme** with ADO blue accent.
- **Version** displayed in the title bar, including git commit hash (e.g., `v0.2.0 (a3b4c5d)`) for detecting stale instances.
- **AI triage** — pluggable investigation backend (see `docs/investigation.md`) with rule-based fallback when no backend is configured.
- **Triage board selector** — dropdown to switch between configured ADO triage boards with a loading indicator while data refreshes.
- **Investigation launcher** — press `i`/`I` to launch AI-powered investigation sessions for triage items. Requires a configured `InvestigationLauncher` (see `docs/investigation.md`).
- **Dynamic settings** — investigation model and agent dropdowns are populated from the active launcher at runtime.
- **Title cleanup** — board name prefixes are automatically stripped from triage item titles for cleaner display.
- **Search** — press `/` to open a search bar that filters the active tab's table in real-time. Press `Enter` to keep the filter, `Escape` to clear it. Works on My PRs, Reviewing, Work Items, and Copilot Sessions tabs.

## How It Works

ADO Dashboard is a [Textual](https://textual.textualize.io/) TUI. It calls the `az` CLI asynchronously to fetch data from Azure DevOps, keeping the UI responsive. Detail views fetch richer metadata in the background (`az repos pr show`, `az boards work-item show`). Triage data comes from a configurable PowerShell script (see `docs/triage-and-investigation.md`). Investigation sessions are launched via the configured `InvestigationLauncher` adapter (see `docs/investigation.md`).

---

## Architecture at a Glance

```
ado-dashboard (CLI)
  └─ WipDashboardApp (Textual App)
       └─ DashboardScreen          ← 5-tab layout, all data workers
            ├─ ado_client          ← az CLI subprocess wrapper (async)
            ├─ triage_client       ← PowerShell script runner (async)
            ├─ session_client      ← ~/.copilot/session-state scanner
            ├─ investigation       ← pluggable InvestigationLauncher adapter`n            ├─ triage_categorizer  ← pure rule-based categorizer + AI merger
            ├─ triage_cache        ← file cache for AI triage JSON
            ├─ investigation_prompts ← prompt builders (delegates to launcher)
            ├─ DetailScreen        ← single-item detail view
            └─ SettingsScreen      ← config form with live model/agent discovery
```

All ADO communication is via the `az` CLI — no HTTP library is used. Long-running fetches run on Textual `@work` workers (async, never blocking the UI thread). AI triage results are written by the investigation backend and polled from a JSON cache file.

### Key modules

| Module | Role |
|---|---|
| `config.py` | 4-layer config resolution (CLI > env > file > defaults); module globals |
| `models.py` | Pure dataclasses: `PullRequest`, `WorkItem`, `TriageItem`, `CopilotSession` |
| `ado_client.py` | `az repos` / `az boards` async wrappers with friendly error translation |
| `triage_client.py` | Runs `Get-TriageItems.ps1`; extracts JSON from mixed stdout |
| `session_client.py` | Parses `workspace.yaml` + `events.jsonl`; launches/resumes sessions in Windows Terminal |
| `window_focus.py` | Win32 ctypes window-focus by PID ancestor chain (no PowerShell) |

---

## For Contributors

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Module map, dependency diagram, async model, screen lifecycle, state ownership |
| [`docs/ado-integration.md`](docs/ado-integration.md) | `az` command shapes, auth assumptions, error handling, JSON mapping |
| [`docs/triage-and-investigation.md`](docs/triage-and-investigation.md) | PowerShell script contract, categorizer pipeline, AI enrichment, investigation launcher |
| [`docs/investigation.md`](docs/investigation.md) | Pluggable InvestigationLauncher adapter: NoOpLauncher, AgencyLauncher, custom backends |
| [`docs/configuration.md`](docs/configuration.md) | Full 4-layer resolution, config schema, setup wizard, in-app settings |
| [`docs/development.md`](docs/development.md) | Running locally, tests, adding a tab, adding a settings field, CSS conventions, known cruft |
