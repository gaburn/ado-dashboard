# ADO Integration

WIP Dashboard calls the `az` CLI (Azure CLI with the `azure-devops` extension) as an async subprocess. There is no direct HTTP or ADO SDK usage.

---

## Prerequisites

| Requirement | Check |
|---|---|
| `az` on `PATH` | `az --version` |
| Authenticated | `az login` (or a service principal via `AZURE_*` env vars) |
| `azure-devops` extension | `az extension add --name azure-devops` |

`ado_client._run_az` calls `shutil.which("az")` at runtime; a missing binary raises `ADOClientError` immediately with an install link.

---

## Command Shapes

All commands append `--output json` and capture stdout for parsing.

### Pull Requests

| Operation | Command skeleton |
|---|---|
| My PRs (per project) | `az repos pr list --creator <email> --status active --top 50 --org <org> --project <project>` |
| Reviewing PRs (per project) | `az repos pr list --reviewer <email> --status active --top 50 --org <org> --project <project>` |
| PR detail | `az repos pr show --id <id> --org <org>` |

PR queries are fanned out across all configured `config.PROJECTS` with `asyncio.gather`. Results are merged and deduplicated (Reviewing tab strips PRs that also appear in My PRs).

### Work Items

| Operation | Command skeleton |
|---|---|
| Assigned WIs (WIQL) | `az boards query --wiql "<WIQL>" --org <org> --project <project>` |
| Batch parent fetch | Same WIQL form with `WHERE System.Id IN (...)` |
| WI detail | `az boards work-item show --id <id> --org <org>` |

The WIQL for assigned work items excludes states: `Closed`, `Removed`, `Done`, `Completed`, `Cut`, `Resolved`.

Work items are fetched with a two-level parent walk: the initial WIQL result is augmented with parent IDs (and their parents) to build a display hierarchy. Parents not assigned to the user are flagged `is_context_parent=True` and rendered dimmed.

---

## Auth Assumptions

- The `az` CLI must be pre-authenticated (`az login`). The app makes no auth calls itself.
- All queries use the configured `ORG_URL` (e.g., `https://dev.azure.com/your-org`).
- The `ADO_PROJECT` / `PROJECTS` config values must match existing ADO projects the account has read access to.

---

## Error Handling

`ado_client._raise_helpful_error` translates common stderr patterns into user-friendly messages:

| stderr pattern | Message shown |
|---|---|
| `please run 'az login'` / `AzureConnectionError` | "Not authenticated. Run `az login` first." |
| `requires the extension 'azure-devops'` | "Run `az extension add --name azure-devops`." |
| `'az repos' is not recognized` | Same extension message. |
| Anything else | Raw exit code + first 1000 chars of stderr. |

All fetch calls in `DashboardScreen._load_data` are wrapped in `try/except Exception`; failures surface as `self.notify(...)` toasts with `severity="error"` and log to `wip-dashboard.log`. Tabs remain visible with empty data rather than crashing.

---

## JSON Mapping

`PullRequest.from_az_json` and `WorkItem.from_az_json` are classmethods on the model dataclasses — they consume the raw dict from `az repos pr list/show` and `az boards query/work-item show` respectively. ADO date strings (up to 7 fractional-second digits) are normalised in `_parse_ado_date`.
