# Client Onboarding Guide

Get your SDD workspace running with governed bootstrap and agent command packs.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://astral.sh/uv) (required)

## Quick Start (One Command)

> Prerequisite: install the SDD CLI first — see [Step 1](#step-by-step-setup-client-project)
> below if you haven't already.

After `sdd wizard run` has generated your project template, `sdd init --default`
runs the full client bootstrap chain in one step: workspace profile, governance
generate (`--full-bootstrap`), skills bootstrap (`--full-bootstrap
--regenerate-seeds`), runtime validation, and git hooks install. It is
equivalent to `sdd init --type client --name local-dev --force`, with any of
`--type`/`--name`/`--force` you pass explicitly taking precedence.

```bash
cd <your-project>
sdd wizard run
sdd init --default
sdd governance validate
```

Each step is skipped automatically if it already ran (idempotent re-run); use
`--force` (or `--default`, which implies it) to re-run all steps.

## Step-by-step Setup (Client Project)

```bash
# 1. Install SDD CLI (cross-platform: Linux/macOS/Windows, no clone required)
uv tool install "git+https://github.com/SergioLacerda/sdd-harness#subdirectory=packages/interfaces/sdd_cli"

# 2. Enter your project and run the wizard
cd <your-project>
sdd wizard run

# 3. Activate runtime/governance in the generated template
#    (this single command also runs steps 4-6 below automatically)
sdd init --type client --name <your-project> --force

# 4. Compile + generate + sign + handshake
sdd governance generate --full-bootstrap

# 5. Generate skills/commands/seeds for agent entrypoints
sdd skills --full-bootstrap --regenerate-seeds

# 6. Verify runtime/governance health and install git hooks
sdd runtime status
sdd setup git-hooks
sdd governance validate
```

### Zero-state onboarding behavior

`sdd wizard run` supports first-run onboarding in an empty workspace.

- If `.sdd/` and `generated/` are absent, the wizard bootstraps Phase 1/2 inputs automatically.
- Minimal folders are created under `generated/client/build/`:
  - `docs-meta/`
  - `phase-1-choices/`
  - `phase-2-input/`
- Runtime activation is intentionally deferred to step 3 (`sdd init` + bootstrap commands).

## Agent Custom Commands (Slash/Prompt Packs)

Custom command packs are generated from canonical `.sdd` artifacts.

- Copilot prompts: `.github/prompts/*.prompt.md`
- Cursor rules: `.cursor/rules/sdd-commands.mdc`
- Codex commands: `.codex/commands.md` + `.codex/skills/*.prompt.md`
- Gemini commands: `.gemini/commands.md`

Core aliases include: `/sdd-ask`, `/sdd-organize`, `/sdd-diagnose`.

To regenerate:

```bash
sdd skills --full-bootstrap
```

## CLI Reference

For authoritative flags and command contracts:

- `docs/spec/reference/commands/cli.md`

## Telemetry

Compliance events are written to `.sdd/runtime/compliance-events.jsonl` (JSONL, append-only).

```bash
# View latest events
cat .sdd/runtime/compliance-events.jsonl | tail -20

# Filter violations only
grep '"event": "VIOLATION"' .sdd/runtime/compliance-events.jsonl
```

To override the log path: `export SDD_COMPLIANCE_LOG=/path/to/events.jsonl`
To disable writes: `export SDD_COMPLIANCE_LOG=disabled`

## Troubleshooting

### `/sdd-ask` returns `API Error: 500`

This usually indicates a provider/IDE API incident, not a local SDD CLI failure.

1. Stop retrying the same slash command in the IDE for that turn.
2. Run the local governed fallback in terminal:

```bash
sdd runtime status
sdd governance validate
sdd ask --full "<your question>"
```

1. Capture the `request_id` from the 500 response and report it for incident triage.
