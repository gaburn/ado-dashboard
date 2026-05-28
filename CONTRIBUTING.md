# Contributing to ADO Dashboard

Thanks for your interest in contributing! ADO Dashboard is a Textual TUI for managing Azure DevOps work items and pull requests, and contributions of all kinds are welcome.

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Azure CLI** with the `azure-devops` extension, authenticated via `az login`
- **PowerShell 7+** — only required if you use the triage tab
- **Windows Terminal** — only required if you use the investigation launcher on Windows

### Setup

```bash
git clone https://github.com/gaburn/ado-dashboard.git
cd ado-dashboard
pip install -e ".[dev]"
ado-dashboard
```

On first launch the setup wizard walks you through configuration. Re-run it any time with `ado-dashboard --setup`.

## Development

### Project Structure

```
src/ado_dashboard/      # Package source
  __main__.py           # Entry point + CLI argument parsing
  app.py                # Textual App subclass
  screens/              # Dashboard, detail view, settings screen
  ado_client.py         # Async wrapper around the `az` CLI
  session_client.py     # Copilot CLI session discovery + Windows Terminal launcher
  triage_client.py      # Runs the user-supplied PowerShell triage script
  triage_categorizer.py # AI / rule-based categorization
  investigation.py      # Pluggable InvestigationLauncher Protocol
  config.py             # 4-layer config resolution (CLI → env → file → defaults)
  setup_wizard.py       # First-run interactive wizard
  models.py             # Dataclasses for PRs, work items, triage items, sessions
  styles/app.tcss       # Textual CSS
  scripts/              # Bundled .example scripts (PowerShell triage template)

src/tests/              # pytest suite
docs/                   # Architecture, configuration, integration, development docs
```

### Scripts

| Command | Description |
|---|---|
| `ado-dashboard` | Run the app locally |
| `ado-dashboard --setup` | Re-run the configuration wizard |
| `pytest` | Run the test suite |
| `ruff check src/` | Lint the package |

### Tech Stack

- **Framework**: [Textual](https://textual.textualize.io/) (async terminal UI)
- **Language**: Python 3.12+
- **External CLIs**: `az` (Azure DevOps), `pwsh` (triage script), optional Copilot/`agency` CLI for the investigation launcher
- **Build backend**: [hatchling](https://hatch.pypa.io/)

## Making Changes

1. **Fork** the repository
2. **Create a branch** for your change (`git checkout -b my-feature`)
3. **Make your changes** — keep commits focused and descriptive
4. **Test locally** — run `pytest` and `ruff check src/`
5. **Submit a pull request** with a clear description of what changed and why

### Code Style

- Type-annotated where it adds clarity; we do not enforce strict typing project-wide yet
- Async-first for any I/O — never block the Textual event loop on `subprocess.run`; use `asyncio.create_subprocess_exec`
- Comments only where the code needs clarification — don't over-comment
- TCSS lives in `src/ado_dashboard/styles/app.tcss`; prefer CSS classes over inline `styles=`

### Architecture Notes

See [`docs/architecture.md`](./docs/architecture.md) for the module map, async/worker model, and screen lifecycle. Adding a new tab? Start with [`docs/development.md`](./docs/development.md).

## Reporting Issues

Use [GitHub Issues](https://github.com/gaburn/ado-dashboard/issues) to report bugs or request features. Include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (OS, Python version, terminal)

For security issues, see [SECURITY.md](./SECURITY.md) — please do **not** open a public issue.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).
