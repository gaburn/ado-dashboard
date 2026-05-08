# Triage and Investigation

---

## Get-TriageItems.ps1 Contract

**Location:** `src/wip_dashboard/scripts/Get-TriageItems.ps1.example` (template).

To use the triage tab:
1. Copy `Get-TriageItems.ps1.example` to a location you own.
2. Fill in your area paths, team names, and ADO org/project (all marked with `<YOUR_...>` placeholders).
3. Set `triage_script_path` in your config (Settings screen → `triage_script_path`, or `config.json`).

wip-dashboard does **not** auto-resolve the bundled `.example` file.  If `triage_script_path` is not set, the triage tab will show an error prompting you to configure it.

### Inputs (CLI Parameters)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `-Board` | string | `''` (→ first board in config) | Board key matching an entry in `$BoardConfig` |
| `-Team` | string | `''` | Team display name from board URL (alternative to `-Board`) |
| `-BoardColumn` | string | `Triage` | ADO board column to query |
| `-ThrottleLimit` | int | `8` | Max parallel `az boards work-item show` calls |

`triage_client.fetch_triage_items` extracts the team name from a board URL using `_extract_team_from_url`, then calls the script with `-Team <name>`. Legacy `-Board` keys are used when no URL is available.

### Output (stdout)

A JSON array of objects, one per work item:

```json
[
  {
    "id": 12345678,
    "title": "...",
    "board": "myboard",
    "description": "...",   // HTML stripped, max 500 chars
    "createdDate": "YYYY-MM-DD",
    "ageDays": 5,
    "assignedTo": "Display Name",
    "prId": 1234567,         // null if no PR reference found
    "tags": "tag1; tag2",
    "priority": 2,           // null if unset
    "workItemType": "Bug"
  }
]
```

Status/diagnostic lines should be written to **stderr**; stdout must contain only the JSON array (non-JSON prefix/suffix lines are tolerated and stripped by `triage_client._extract_json_array`).

`TriageItem.from_json` maps this dict to the `TriageItem` dataclass.

---

## Categorizer Pipeline

`triage_categorizer.categorize_triage_items(items)` is a pure function (no I/O):

```
fetch_triage_items()
  → [TriageItem, ...]
  → categorize_triage_items()         # rule-based pass
      → _classify(item)               # regex first-match: Blocking / PR Review / Bug / Feature / Support
      → _effective_priority(item)     # ADO priority if set, else category default
      → _urgency_rank(item, priority) # base_score(priority) + min(age_days, 90)
      → groups: {1: [...], 2: [...], 3: [...], 4: [...]}
  → generate_action_plan(groups)      # deterministic 2-3 line plan (no AI)
  → displayed immediately
```

Classification rules (first match wins):

| Pattern | Category |
|---|---|
| `block\|fail\|broke\|404\|500\|outage\|...` in title+description | Blocking Issue |
| `pr_id is not None` or `pr review\|pull request` in title | PR Review |
| `work_item_type == "Bug"` or `bug\|not working\|regression\|...` | Bug / Behavior |
| `work_item_type in (Feature, User Story)` or `feature\|enhancement\|...` | Feature Request |
| _(otherwise)_ | Support Question |

Urgency rank = `base_score[priority] + min(age_days, 90)`, where base scores are `{1:400, 2:300, 3:200, 4:100}`.

---

## AI Enrichment

When `config.AI_TRIAGE_MODE == "copilot"` (default), the dashboard attempts AI enrichment after the rule-based pass:

1. **Cache check** — `triage_cache.is_cache_fresh(board_url)`: if the cache file exists and is < `TRIAGE_CACHE_MAX_AGE_SECONDS` (default 1800s), apply it immediately.
2. **Launch** — the configured `InvestigationLauncher.launch(prompt, ...)` is called.  With the default `NoOpLauncher`, AI enrichment will be skipped (the launcher returns failure).  Configure an `AgencyLauncher` or custom backend to enable it — see `docs/investigation.md`.
3. **Poll** — `set_interval(4, _poll_copilot_triage)` checks `cache_mtime > launch_time` every 4 seconds.
4. **Apply** — `apply_ai_analysis(items, analysis)` merges AI-assigned `category`, `ai_priority`, and `ai_why` into items in place, then rebuilds priority groups.
5. **Timeout** — after 5 minutes the poll timer stops and the rule-based results remain.

### Cache file format

Written by the investigation session to `~/.wip-dashboard/triage/<board_key>.json`:

```json
{
  "board": "myboard",
  "timestamp": "2025-01-01T12:00:00Z",
  "items": [
    {"id": 12345678, "category": "Blocking Issue", "priority": 1, "why": "Pipeline failing on deploy"}
  ],
  "action_plan": "Start with P1 blockers..."
}
```

`triage_cache.read_cached_triage` checks for partial writes (file must end with `}`), validates the `items` key, and falls back to `None` on any parse error.

---

## Investigation Launcher

Two investigation modes are available from `DashboardScreen`:

| Key | Scope | Prompt builder |
|---|---|---|
| `i` | Selected item | `build_item_investigation_prompt(id, title, board_url, category, priority)` |
| `I` | Entire board | `build_board_investigation_prompt(board_url, board_display_name)` |

Both call `session_client.launch_investigation(prompt, title, cwd=config.REPO_ROOT, model=..., agent=...)`, which delegates to the active `InvestigationLauncher`.

See `docs/investigation.md` for how to configure a launcher.

---

## Window Focus (`f` key)

`window_focus.focus_terminal_by_pid(pid)` uses pure Win32 ctypes (no subprocess):

1. `CreateToolhelp32Snapshot` → builds `{child_pid: parent_pid}` map.
2. Walks up from `pid` collecting ancestor PIDs.
3. `EnumWindows` → finds a visible top-level window whose process is in the ancestor set.
4. `ShowWindow(SW_RESTORE)` + Alt-key trick + `SetForegroundWindow`.

The shell PID stored in `CopilotSession.pid` comes from `session_client._get_active_session_pids`, which walks from `copilot.exe` upward to find the nearest `pwsh`/`cmd` ancestor.
