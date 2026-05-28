# Development Guide

---

## Running Locally

```bash
# Clone and install in editable mode (requires Python 3.12+)
cd wip-dashboard
pip install -e .

# First run — triggers the setup wizard
ado-dashboard

# Re-run the wizard
ado-dashboard --setup

# Override config at the CLI without editing files
ado-dashboard --org https://dev.azure.com/myorg --user me@example.com
```

Logs are written to `<repo-root>/ado-dashboard.log` (overwritten each run). Set `logging.DEBUG` is already on for `ado_dashboard.*` and `textual.*`.

---

## Tests

The test suite lives in `src/tests/`. At the time of writing the directory contains only `__init__.py` — no tests have been written yet.

```bash
pytest src/tests/
```

The package uses `hatchling` as its build backend. No test runner config exists in `pyproject.toml`; `pytest` defaults apply.

---

## Adding a Tab

1. **Define the data model** in `models.py` if needed (frozen dataclass, `from_az_json` / `from_json` factory).
2. **Add a fetch function** in `ado_client.py` (or a new `*_client.py`). Use `async def` + `asyncio.create_subprocess_exec` for subprocess calls.
3. **Add a `TabPane`** in `DashboardScreen.compose` (in `screens/dashboard.py`):
   ```python
   with TabPane("New Tab", id="new-tab"):
       yield DataTable(id="new-table", cursor_type="row", zebra_stripes=True)
   ```
4. **Add columns** in `_setup_columns`.
5. **Add a `_populate_new_table` static method** following the existing pattern.
6. **Integrate into `_load_data`**: add a fetch-and-populate coroutine, include it in the `asyncio.gather` call in Stage 2.
7. **Add keyboard binding** in `DashboardScreen.BINDINGS` (e.g., `Binding("6", "switch_tab('new-tab')", "New Tab")`).
8. **Add a sort key dict** (`_NEW_SORT_KEYS`) and wire it into `action_sort_column`.
9. **Add CSS** in `styles/app.tcss` if the new tab needs custom styling.

---

## Adding a Settings Field

1. **Add a module global** in `config.py` with an env-var fallback and a `_DEFAULT_*` constant.
2. **Add loading** in `config.load_from_file`: check `"ENV_VAR" not in os.environ and "key" in file_data`.
3. **Add CLI override** in `config.apply_overrides` if CLI access is needed.
4. **Add to `_FIELDS`** in `screens/settings.py`:
   ```python
   ("my_new_key", "Human Label", False),  # False = Input, True = Switch
   ```
5. **Add to `_CONFIG_ATTR_MAP`** in `settings.py` mapping `"my_new_key"` → `"MY_CONFIG_ATTR"`.
6. **Add to the setup wizard** in `setup_wizard.run_setup` if it should be collected on first run.
7. **Document** in `docs/configuration.md`.

---

## Style / CSS Conventions

Styles live in `src/ado_dashboard/styles/app.tcss` (a single file; Textual CSS, not standard CSS).

Key palette variables declared at the top:

| Variable | Value | Use |
|---|---|---|
| `$accent` | `#0078d4` | ADO blue — header, key indicators, focus rings |
| `$surface` | `#1e1e1e` | Screen background |
| `$surface-raised` | `#252526` | Panel / footer background |
| `$surface-overlay` | `#2d2d30` | Hover overlays, collapsible headers |
| `$border-subtle` | `#3e3e42` | Dividers |
| `$text-primary` | `#cccccc` | Default text |
| `$text-muted` | `#848488` | Dimmed text, footer labels |
| `$approved-color` | `#2ea043` | Reviewer approved |
| `$rejected-color` | `#da3633` | Reviewer rejected |

**Conventions:**

- Use `$accent` variables (not hardcoded hex) for any color that should follow the theme.
- Widget IDs use `kebab-case` (e.g., `#pr-table`, `#triage-scroll`).
- CSS classes use `kebab-case` (e.g., `.triage-empty`, `.section-heading`).
- Rich `Text` objects with inline styles (e.g., `Text("✓", style="bold green")`) are used for per-row coloring rather than CSS, because DataTable cells are Rich renderables.

---

## Known Cruft / Cleanup Candidates

The following files in `src/` are scratch/debug artifacts from development and are **not part of the package**. They are not imported anywhere in the package code.

| File | Description |
|---|---|
| `src/parse_final.py` | Scratch script — likely early HTML-parsing experiments |
| `src/parse_regex.py` | Scratch script — regex parsing experiments |
| `src/parse_threads.py` | Scratch script — PR thread parsing experiments |
| `src/find_threads.py` | Scratch script — PR thread finder |
| `src/check_status.py` | Scratch script — status check utility |
| `src/test_parse.py` | Scratch test / one-off runner |
| `src/PR_14992655_threads.json` | Raw PR thread data blob (debug capture) |
| `src/PR_14992655_threads_clean.json` | Cleaned PR thread data blob (debug capture) |

These files sit in `src/` outside the `ado_dashboard` package directory, so they are excluded from wheel builds (hatch only packages `src/ado_dashboard`). They are safe to delete when no longer needed for reference.

**Ambiguity note:** It is unclear whether `parse_*.py` / `find_threads.py` / `check_status.py` represent prototype code that was later incorporated into `Get-TriageItems.ps1`'s inline Python, or are independent investigations. Review before deleting if in doubt.
