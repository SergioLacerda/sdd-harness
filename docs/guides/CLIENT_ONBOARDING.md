# Client Onboarding Guide

Get your SDD workspace running with governed bootstrap and agent command packs.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://astral.sh/uv) (optional, installed by `setup.sh`)

## Step-by-step Setup

```bash
# 1. Clone
git clone https://github.com/SergioLacerda/sdd-harness.git
cd sdd-harness

# 2. Install environment
make install
source .venv/bin/activate

# 3. Initialize workspace/runtime (client profile by default)
sdd init --full-bootstrap

# 4. Compile + generate + sign + handshake
sdd governance generate --full-bootstrap

# 5. Generate skills/commands/seeds for agent entrypoints
sdd skills --full-bootstrap

# 6. Verify runtime/governance health
sdd runtime status
sdd governance validate
```

## Agent Custom Commands (Slash/Prompt Packs)

Custom command packs are generated from canonical `.sdd` artifacts.

- Copilot prompts: `.github/prompts/*.prompt.md`
- Cursor rules: `.cursor/rules/sdd-commands.mdc`
- Codex commands: `.codex/commands.md` + `.codex/skills/*.prompt.md`
- Gemini commands: `.gemini/commands.md`

Core aliases include: `/sdd-ask`, `/sdd-ask-full`, `/sdd-organize`, `/sdd-diagnose`.

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
sdd ask-full "<your question>"
```

3. Capture the `request_id` from the 500 response and report it for incident triage.
