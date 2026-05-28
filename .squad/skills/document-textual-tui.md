# Skill: Document an Existing Textual TUI Codebase

## When to use

When dropped into an undocumented Python Textual application and asked to produce contributor/architecture docs from source.

## Reading order

Read files in this order for maximum signal with minimum round-trips:

1. `pyproject.toml` — dependencies (esp. HTTP library vs CLI-based), entry point, Python version
2. `__main__.py` — startup sequence, arg parsing, config loading, what's launched
3. `app.py` — theme, CSS path, initial screen push
4. `config.py` — config resolution layers, module globals
5. `models.py` — data model: what entities exist and how they are parsed
6. `screens/dashboard.py` (paginate!) — worker pattern, tab layout, data flow, AI enrichment, keybindings
7. `screens/detail.py`, `screens/settings.py` — secondary screens, what they return
8. `*_client.py` files — external communication: async subprocess? HTTP? filesystem?
9. `styles/app.tcss` — skim palette variables and major widget selectors
10. `src/` root — check for stray scratch files outside the package directory

## Key questions to answer from source

- What is the only declared dependency? (No HTTP lib → it shells out.)
- What is the `@work` decorator usage? (exclusive? group? — determines concurrency model)
- Where is state mutated? (module globals in `config.py`? instance attrs on Screen?)
- Is the setup wizard the only way to configure, or does the in-app settings screen also write?
- Are there scratch/debug files outside the package directory?

## Docs structure that works

```
docs/
  architecture.md       module map + Mermaid diagram + async model + state map
  ado-integration.md    CLI command shapes, auth, error handling
  triage-and-investigation.md  script contract, categorizer, AI enrichment, launcher
  configuration.md      4-layer table, full JSON schema, wizard fields
  development.md        running, tests, how-to-add-X, CSS conventions, known cruft
```

README: keep user-facing content; add "Architecture at a glance" ASCII/Mermaid + "For contributors" table with doc links.

## Ambiguity markers to include explicitly

- "This mapping is hard-coded. New boards require a code change."
- "The setup wizard does NOT collect X — configure via Settings or env var."
- "Unclear whether scratch files are prototype or investigation — review before deleting."

## Common surprises in Textual apps

- `@work(exclusive=True)` means only one instance of that worker runs at a time; a new call cancels the prior one.
- DataTable rows store Rich `Text` objects for per-row styling — CSS can't target individual rows.
- `Screen[T]` generic return type signals what `dismiss(value)` passes back to the caller.
- `set_interval` timer handles must be stored and stopped manually on board/state changes.
