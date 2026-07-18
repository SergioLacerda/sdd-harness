# Client Onboarding Guide

Get your SDD workspace running with governed bootstrap and agent command packs.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://astral.sh/uv) (required)

## Quick Start (One Command)

> Prerequisite: install the SDD CLI first — see [Step 1](#step-by-step-setup-client-project)
> below if you haven't already.

After `sdd install --wizard` has generated and deployed your project template,
`sdd init --default` runs the full client bootstrap chain in one step: workspace
profile, governance generate (`--full-bootstrap`), skills bootstrap
(`--full-bootstrap --regenerate-seeds`), and runtime validation. It is
equivalent to `sdd init --type client --name local-dev --force`,
with any of `--type`/`--name`/`--force` you pass explicitly taking precedence.

```bash
cd <your-project>
sdd install --wizard
sdd init --default
sdd governance validate
```

`sdd install --wizard` deploys generated files into the project root by default.
Use `--only-template` to stop after producing `generated/client/build/final-template/`.
It also supports `--from-file <path>` (bring your own governance JSON) and
`--non-interactive` (skip prompts) — see `docs/spec/reference/commands/cli.md`
for the full flag reference.

Each step is skipped automatically if it already ran (idempotent re-run); use
`--force` (or `--default`, which implies it) to re-run all steps.

## Step-by-step Setup (Client Project)

> The official, CI-proven install channel is the GitHub Release wheelhouse
> (`dist/` assets attached to a tagged
> [GitHub Release](https://github.com/SergioLacerda/sdd-harness/releases),
> installed with `pip install --no-index --find-links <dist-dir> sdd-cli`).
> `.github/workflows/release.yml` verifies this exact install on
> `windows-latest` and `ubuntu-latest` before publishing. The
> `uv tool install` command below is a source/development install path that
> tracks branch code rather than a released version.

```bash
# 1. Install SDD CLI (cross-platform: Linux/macOS/Windows, no clone required)
uv tool install "git+https://github.com/SergioLacerda/sdd-harness#subdirectory=packages/interfaces/sdd_cli"

# 2. Enter your project and run the wizard
cd <your-project>
sdd install --wizard

# 3. Activate runtime/governance in the generated template
#    (this single command also runs steps 4-6 below automatically)
sdd init --type client --name <your-project> --force

# 4. Compile + generate + sign + handshake
sdd governance generate --full-bootstrap

# 5. Generate skills/commands/seeds for agent entrypoints
sdd skills --full-bootstrap --regenerate-seeds

# 6. Verify runtime/governance health
sdd runtime status
sdd governance validate
```

### Windows signing troubleshooting

Key generation (`sdd governance keygen`), signing (`sdd governance sign`,
full bootstrap), and runtime signature verification all use a native Ed25519
backend (the `sdd-compile` binary) and do not shell out to OpenSSL — Windows
standalone installs do not require `openssl.exe` on `PATH`.

The `sdd-compile` binary itself is resolved in this order: `SDD_COMPILE_BIN`
env var → repo-local build → `PATH` → binary bundled in the sdd-core wheel →
download from the matching GitHub Release.

Only wheels built by the release CI bundle the native binaries. A source
install (for example `uv tool install "git+https://...#subdirectory=..."`)
has no bundled binary and falls back to the release download, which requires
working TLS certificate verification. If that download fails with
`CERTIFICATE_VERIFY_FAILED`, either:

- install from the release wheelhouse instead (the CI-proven channel above:
  `pip install --no-index --find-links <dist-dir> sdd-cli`) — the bundled
  binary makes the download unnecessary; or
- download `sdd-compile-windows-amd64.exe` from the GitHub Release manually
  and point `SDD_COMPILE_BIN` at it; or
- behind a TLS-intercepting corporate proxy, set `SSL_CERT_FILE` to a CA
  bundle that includes the proxy's certificate.

Full bootstrap and client onboarding use the default key id `dev-01`, so an
idempotent bootstrap can print:

```text
Key dev-01 already exists at .sdd\trust\dev-01.key
```

That line is informational. A direct command such as
`sdd governance sign --key-id my-org-01` resolves
`.sdd\trust\my-org-01.key`; it does not fall back to `dev-01`. To use a custom
key id directly, generate it first:

```bash
sdd governance keygen --key-id my-org-01
sdd governance sign --key-id my-org-01
```

### Zero-state onboarding behavior

`sdd install --wizard` runs a single guided flow in an empty workspace — no
phase menu, no manual staging required:

1. Language, hook-mode, and agent-selection prompts (skippable via
   `--non-interactive`)
2. Governance generation (or `--from-file <path>` to supply your own)
3. Compilation and seed generation into `generated/client/build/`
4. Deployment of the final template into the project root

Runtime activation is intentionally deferred to step 3 (`sdd init` + bootstrap commands).

### Seedling Selection

The interactive seedling selector groups options into four sections:

- **CORE** — `governance`, `agents-md`, `prompt-commands`, `activation-guide`,
  `verify`. Always part of the recommended default.
- **IDEs** — `vscode`, `cursor`, `antigravity`.
- **AGENTS** — `claude`, `codex`, `gemini`, `copilot`.
- **OPTIONAL** — `ci`, `compliance`, `personal-overlay`. Off by
  default; select explicitly to generate `.github/workflows/sdd-validation.yml`
  or `compliance.seed.json`.

Leaving the selection empty applies the **recommended default** (CORE + all
IDEs + all AGENTS) — it is not "generate everything," and it never includes
CI/CD or compliance artifacts unless you opt in.

Only the artifacts belonging to your selection are generated, deployed, and
validated. Files from a previous wizard run that belong to options you no
longer select are **not** deleted automatically — a future `--prune-unselected`
mode may add that, but the current behavior never removes files on its own.

## Agent Custom Commands (Slash/Prompt Packs)

Custom command packs are generated from canonical `.sdd` artifacts.

- Copilot prompts: `.github/prompts/*.prompt.md`
- Cursor rules: `.cursor/rules/sdd-commands.mdc`
- Codex commands: `.codex/commands.md` + `.codex/skills/*.prompt.md`
- Gemini commands: `.gemini/commands.md`

Core aliases include: `/sdd-ask`, `/sdd-organize`, `/sdd-diagnose`.

`/sdd-ask` is a thin adapter over the CLI command `sdd ask`. The CLI is the
single governed source of truth for intent classification, execution gate, and
handoff guidance; slash commands and prompt-submit hooks must not classify or
route independently. When `sdd ask` reports implementation intent, it emits a
governed handoff (`next_valid_path: implementation_handoff`) for the calling
agent. It does not execute implementation, bind a provider, or invoke an
analysis skill automatically; the structured fields `delegation_executed` and
`provider_bound` remain `false` until a future explicit delegation contract
exists.

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
