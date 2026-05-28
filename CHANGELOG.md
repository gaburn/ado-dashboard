# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-28

### Added
- **Demo mode** (`--demo` flag / `ADO_DASHBOARD_DEMO=1` env var): bypasses all Azure DevOps calls and renders every tab with fictional Tolkien-themed fixture data. Ideal for screenshots, presentations, and onboarding without exposing real org/project data. A `🎭 DEMO MODE` banner appears in the status bar and app subtitle.
- **README screenshots** — hero image plus per-tab gallery captured in demo mode, stored under `docs/screenshots/`.
- **CI guard** (`guard-no-squad-on-main`) — fails any push or PR that introduces Squad framework files onto `main`.

### Changed
- **Public-readiness sweep:** LICENSE attribution, CONTRIBUTING/SECURITY/CODE_OF_CONDUCT polish, packaging metadata, pre-commit config, release workflow with PyPI Trusted Publishing.
- **Code of Conduct enforcement reports** now route through GitHub private security advisories instead of a maintainer email address.

## [0.2.1] - 2026-01-01

### Added
- `platformdirs` declared as explicit runtime dependency (previously transitive via `textual`).
- Build string now includes git tags via `git describe --tags`, making the version visible in the TUI subtitle.
- Release workflow (`.github/workflows/release.yml`) using PyPI Trusted Publishing (OIDC) — no API tokens required.

### Changed
- **App renamed from `wip-dashboard` to `ado-dashboard`** across all entry points, config keys, and documentation.
- Environment variable `WIP_DASHBOARD_REPO_ROOT` superseded by `ADO_DASHBOARD_REPO_ROOT`; old name still accepted with a deprecation warning until v0.4.0.
- **"Sessions" tab renamed to "Copilot Sessions"** for clarity in the TUI sidebar.
- Subtitle no longer displays the redundant static version string; only the `__build__` value (from `git describe`) is shown.
- Organization URL input in the setup wizard now normalises bare org names (e.g. `myorg`) to the full `https://dev.azure.com/myorg` URI automatically.
- `textual` dependency pinned to `>=3.0.0,<5` to avoid silent breakage on a future major release.
- Log file relocated from the install directory (unwritable in `site-packages`) to `platformdirs.user_log_path("ado-dashboard")`.

### Deprecated
- `WIP_DASHBOARD_REPO_ROOT` environment variable — will be removed in **v0.4.0**. Rename to `ADO_DASHBOARD_REPO_ROOT`.

### Fixed
- Triage tab no longer shows a blank screen when there are no items to triage; an informative empty-state message is displayed instead.
- ADO organization URL normalization prevents a common setup error when users enter a bare org name.

### Migration Notes
- Configuration files previously stored in `~/.wip-dashboard/` are **not** auto-migrated to `~/.ado-dashboard/`. Copy the directory manually if needed.
- The `ado-dashboard` PyPI package replaces the old `wip-dashboard` package. Uninstall the old package before installing the new one.

## [0.2.0] - 2025-01-01

_Initial public release under the `ado-dashboard` name. Prior development history available in git log._

[Unreleased]: https://github.com/gaburn/ado-dashboard/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/gaburn/ado-dashboard/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/gaburn/ado-dashboard/releases/tag/v0.2.0
