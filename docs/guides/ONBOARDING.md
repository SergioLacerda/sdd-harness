# Onboarding Guide (Local Development)

Set up a local development environment for contributing to the SDD Harness codebase itself.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://astral.sh/uv) (required)

## Deploy local + build

```bash
# Clone and bootstrap the workspace (creates .venv, installs all packages + dev/test deps)
git clone https://github.com/SergioLacerda/sdd-harness.git
cd sdd-harness
uv run sdd setup run
```

`uv run` resolves the workspace environment from `pyproject.toml` on demand — no
pre-existing `.venv` or manual activation required, and it works the same on Linux, macOS,
and Windows.

`uv run sdd setup run`:

- creates `.venv` if it doesn't exist
- installs all workspace packages (core, telemetry, runtime, compiler, integration, wizard,
  cli) + dev/test dependencies from root `pyproject.toml`
- validates imports and CLI responsiveness
- installs SDD git hooks (`sdd setup git-hooks`)

> Equivalent via Make (used by CI/automation): `make install`, followed by
> `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows) if you prefer an
> activated shell.

<!-- -->

> [!WARNING]
> If you also have `sdd` installed globally as the `sdd-cli` tool (e.g. via
> `uv tool install`, as an adopter in another project), that global binary may appear
> earlier in your `PATH` and
> shadow this repository's version (`.venv/bin/sdd` or `.venv/Scripts/sdd.exe`). When
> developing in this repo, always prefer `uv run sdd <command>` (uses this workspace's
> `.venv` regardless of `PATH`), or run `uv tool uninstall sdd-cli` before starting.

## Quick bootstrap

```bash
# Bootstrap local governance runtime: profile + governance generate + skills + runtime validate + git hooks
uv run sdd init --default
```

`sdd init --default` is equivalent to `sdd init --type client --name local-dev --force` and
runs the full chain:

1. Workspace profile (`.sdd/profile`)
2. `sdd governance generate --full-bootstrap`
3. `sdd skills --full-bootstrap --regenerate-seeds`
4. `sdd runtime status --force`
5. `sdd setup git-hooks`

```bash
# Restore the pre-commit framework hook chain
make hooks-install
```

> [!NOTE]
> `sdd init --default` always re-installs git hooks via `sdd setup git-hooks` (step 5/5 —
> `--default` implies `--force`), which only links the SDD-internal hooks and does **not**
> preserve the `pre-commit` framework chain. Run `make hooks-install` afterwards to restore
> the chained hook (SDD hooks + `pre-commit` framework). Tracked as a known gap in
> `sdd setup git-hooks`.

```bash
# Verify everything is healthy
uv run sdd runtime status --force
uv run sdd governance validate
```

## Step-by-step (manual / customized)

If you need finer control over individual steps (e.g. re-running just governance
generation, or skipping skills regeneration):

```bash
uv run sdd init --type client --name local-dev --force
make governance-bootstrap   # compile + generate + sign artifacts (= sdd governance generate --full-bootstrap)
uv run sdd skills --full-bootstrap --regenerate-seeds
uv run sdd runtime status --force
uv run sdd governance validate
make hooks-install           # SDD hooks + pre-commit framework chain
```

CLI reference: [`docs/spec/reference/commands/cli.md`](../spec/reference/commands/cli.md)
