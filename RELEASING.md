# Releasing ado-dashboard

## Version Policy

[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

| Bump | When |
|------|------|
| PATCH | Bug fixes, dependency updates, documentation |
| MINOR | New features, non-breaking changes |
| MAJOR | Breaking changes to CLI, config format, or public API |

## Release Steps

1. **Bump the version** in two places:
   - `src/ado_dashboard/__init__.py` — `__version__ = "X.Y.Z"`
   - `pyproject.toml` — `version = "X.Y.Z"`

2. **Update CHANGELOG.md**:
   - Rename `## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD`
   - Add a fresh `## [Unreleased]` section at the top
   - Add the comparison URL at the bottom

3. **Commit the release prep**:
   ```bash
   git add pyproject.toml src/ado_dashboard/__init__.py CHANGELOG.md
   git commit -m "chore: bump version to X.Y.Z"
   ```

4. **Tag the release** (annotated):
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

5. **Push branch and tag**:
   ```bash
   git push origin <branch>
   git push origin vX.Y.Z
   ```

6. The `release.yml` workflow fires automatically on the tag push and:
   - Builds wheel + sdist
   - Publishes to PyPI via OIDC (no secrets needed — see below)
   - Creates a GitHub Release with changelog notes and artifacts

## Pre-flight Checklist

- [ ] `pytest -q` passes with no failures
- [ ] `ruff check src/` is clean (or only known ignores)
- [ ] `python -m build` succeeds locally
- [ ] CHANGELOG `## [Unreleased]` moved to versioned section with today's date
- [ ] `__version__` and `pyproject.toml` `version` are in sync
- [ ] README reflects any new features or changed behaviour
- [ ] Deprecation notices have correct removal version targets

## PyPI Trusted Publishing (OIDC)

No API tokens are stored. Authentication is handled by GitHub's OIDC integration with PyPI.

**One-time setup** (only needed when first publishing the project):

1. Register the project on PyPI (or Test PyPI for a dry run).
2. Go to **PyPI → your project → Publishing → Add a new publisher**:
   - Owner: `gaburn`
   - Repository: `ado-dashboard`
   - Workflow filename: `release.yml`
   - Environment: `pypi`
3. Done. All subsequent releases publish automatically when a `v*.*.*` tag is pushed.

See: <https://docs.pypi.org/trusted-publishers/>
