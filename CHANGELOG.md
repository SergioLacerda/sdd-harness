# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Commit convention:** New entries should follow [Conventional Commits](https://www.conventionalcommits.org/).
> Automation with `git-cliff` or `commitizen` can generate entries from commit messages.

---

## Release Checklist

Before tagging a new release, verify:

- [ ] `make release-dry-run` passes with no errors
- [ ] `README.md` — version number and feature list are up to date
- [ ] `readme-client.md` — client-facing install instructions reflect current CLI commands
- [ ] `readme-detailed.md` — detailed architecture description matches current packages and structure
- [ ] `readme-ia.md` — AI/agent context is accurate for the new release
- [ ] `CHANGELOG.md` — `[Unreleased]` section renamed to `[x.y.z] — YYYY-MM-DD`
- [ ] Git tag created: `git tag vX.Y.Z && git push origin vX.Y.Z`

---

## [Unreleased]

### Added
- `check_module_available()` (in `sdd_core.utils.process`) and `require_dev_module()` (in `sdd_cli.utils.dev_deps`): governance-safe (no `python -c`) checks that give an actionable error instead of a raw `ModuleNotFoundError` traceback when an optional dev tool (`ruff`, `mypy`, `bandit`, `build`) or the `sdd_cli` package itself is missing from the active interpreter, applied to `sdd lint`, `sdd audit` (compliance pack), and `sdd release`.

### Changed
- Breaking change: `sdd_runtime.SkillEngine` no longer accepts legacy short skill aliases (for example `diagnose`, `validate-governance`); only canonical `sdd-*` names are valid, and legacy alias calls now return `legacy_alias_removed` with a canonical-name suggestion.
- Promoted `uv run sdd setup run` as the primary cross-platform local-setup path in `README.md` (works without a pre-existing `.venv` or shell activation on Linux, macOS, and Windows); `make install` is documented as the CI/automation equivalent. Added a PATH-shadowing warning for contributors who also have `sdd-cli` installed globally via `uv tool install`.
- Fixed `Makefile`'s `VENV_PYTHON` detection to also find `.venv/Scripts/python.exe` (Windows venv layout), not just `.venv/bin/python`.
- `sdd setup git-hooks` and `.github/setup-precommit-hook.sh` now fall back to copying hook files when symlinks are unavailable on the platform, instead of failing with an `OSError`/exit 1.

### Removed
- Removed `install.sh` and the legacy `curl | sh` global-install instructions from `README.md` and `docs/guides/CLIENT_ONBOARDING.md`, to avoid ambiguity with the local/`uv`-based install paths.

---

## [1.0.1] — 2026-07-10

### Fixed
- Fixed release workflows to invoke the canonical `sdd governance compile --profile client` command and prepare `generated/client/build/final-template/.sdd` before copying generated governance artifacts.
- Added release wheelhouse dependencies for offline `pip install --no-index --find-links dist sdd-cli` smoke tests on Linux and Windows.
- Fixed standalone `sdd init --default` compiler execution by authorizing official platform-suffixed `sdd-compile-*` release assets as governed compiler binaries.
- Fixed wizard cleanup reporting when standalone install smoke uses a project root outside the generated client build directory.

---

## [0.1.0] — 2026-05-09

### Added
- `sdd init` command — initialises workspace `.sdd/profile` (INI, schema v1) with `--type`, `--name`, `--force` flags; guards against nested workspace creation
- `sdd runtime status` command — shows AHP (Agent Handshake Protocol) + GAP (Governance Activation Protocol) state with exit codes per AHP state
- `sdd governance score` subcommand — weighted governance score formula (profile 30 + artifacts 30 + AHP confidence 20 + core_hash 20 = 100); `--verbose` table, `--threshold` gate
- `sdd doctor run --score-threshold` — aborts if score falls below threshold before running spec diagnostics
- `sdd governance generate` now writes `.github/copilot-instructions.md` from real governance content (MANDATEs, GUIDELINEs, DECISIONs)
- `sdd governance compile` now persists `core_hash[:16]` into `.sdd/profile` after compilation
- `governance_gate()` injected into `LazyCommandGroup.invoke()` — runs AHP on every CLI invocation (exempt: `init`, `version`, `help`)
- `sdd_core.governance.compliance` — append-only JSONL audit log at `.sdd/runtime/compliance-events.jsonl`; events: `WORKSPACE_INIT`, `GOVERNANCE_CHECKED`, `COMPILE_COMPLETE`, `VIOLATION`
- `sdd_core.governance.handshake` — canonical AHP implementation migrated from `tools/`; `tools/governance/agent_handshake.py` becomes a thin wrapper
- `sdd_core.utils.environment`: `WorkspaceNotInitializedError`, `ProfileContext`, `find_workspace_root()`, `resolve_profile()`, `write_profile()`
- `SECURITY.md` — vulnerability disclosure policy and response timeline
- `conftest.py` (root) — `pytest_sessionstart` hook ensures governance compiled artifacts exist before any test session
- `make coverage` target — HTML + terminal-missing report
- `make docs-build` / `make docs-serve` targets — MkDocs build and live preview
- `make docker-build` target
- `make release-dry-run` target — validates version, git tags, and CHANGELOG before release

### Changed
- `make check` now invokes `pytest tests packages` directly (previously `python3 scripts/run_all_tests.py`)
- `--import-mode=importlib` and all `--ignore-glob` flags moved from `scripts/run_all_tests.py` into `[tool.pytest.ini_options] addopts`
- `sdd doctor run` now exits 1 with an actionable message when invoked outside an initialised workspace
- `LazyCommandGroup.invoke()` raises `click.UsageError` on `WorkspaceNotInitializedError` (was silently swallowed)
- `[tool.ruff.lint.mccabe] max-complexity` lowered from 10 → 7
- Root package version bumped from `0.0.0` → `1.0.0` to align with package sub-versions
- `bandit -r packages/ -ll -q` added to `make lint`

### Removed
- `pylint` dependency and `[tool.pylint.*]` configuration (superseded by ruff)
- `"build"` removed from `[tool.uv.workspace].members` (dead entry, namespace collision risk)
- `.spec.config` as profile source — replaced by `.sdd/profile` (INI schema v1)

### Fixed
- AHP `_extract_governance_core()` now searches `generated/*/compiled/` (was wrong path)
- AHP fingerprint uses `[:16]` slice (was `[:8]`, causing hash mismatches)
- AHP Layer 4 checks `generated/*/compiled/` directories
- AHP cache I/O errors now logged as warnings instead of silently suppressed
- `SDD_AGENT_ID` environment variable now respected in AHP

---

## [1.0.0] — 2026-01-01

Initial stable release of the multi-package workspace structure.

- `sdd_core`, `sdd_compiler`, `sdd_telemetry`, `sdd_integration`, `sdd_cli`, `sdd_wizard` as separate uv workspace members
- Governance spec compilation pipeline (`GovernanceOrchestrator` + `DeploymentManager`)
- Agent Handshake Protocol (AHP) v1 — 4-layer validation, 5 states
- `sdd lint spec`, `sdd governance compile`, `sdd governance generate`, `sdd doctor run`
- MkDocs documentation site

[Unreleased]: https://github.com/SergioLacerda/sdd-harness/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/SergioLacerda/sdd-harness/releases/tag/v1.0.1
[0.1.0]: https://github.com/SergioLacerda/sdd-harness/releases/tag/v0.1.0
[1.0.0]: https://github.com/SergioLacerda/sdd-harness/releases/tag/v1.0.0
