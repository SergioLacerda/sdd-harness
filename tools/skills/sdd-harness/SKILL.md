---
name: sdd-harness
description: Expert skill for operating the SDD (Sovereign Digital Design) Governance Runtime and CLI.
---

# SDD Harness Skill

This skill defines the operational protocol for interacting with the SDD Governance Runtime.
Use it for governance operations, runtime diagnostics, and governed command execution.

## Authority And Source Of Truth

Use these files as canonical runtime truth:

- `.sdd/agent-instructions.md` (governance authority)
- `.sdd/commands/registry.json` (active command registry)
- `.sdd/skills/registry.json` (active skill registry)
- `.sdd/commands/<command-id>/command.yaml` (canonical command contract)
- `.sdd/skills/<skill-name>/skill.yaml` (canonical skill contract)

Do not treat `.github/prompts/*.prompt.md` as source of truth for availability.
Prompt files are adapter artifacts and may contain legacy entries.

## Active Governed Command Routes

Resolve from `.sdd/commands/registry.json` + canonical command YAML:

| Slash | CLI route | Canonical file |
|---|---|---|
| `/sdd-ask` | `sdd ask` | `.sdd/commands/sdd-ask/command.yaml` |
| `/sdd-ask-full` | `sdd ask-full` | `.sdd/commands/sdd-ask-full/command.yaml` |
| `/sdd-organize` | `sdd organize` | `.sdd/commands/sdd-organize/command.yaml` |
| `/sdd-audit` | `skill sdd-audit` (canonical execution uses `sdd audit`) | `.sdd/commands/sdd-audit/command.yaml` |

Other entries in `.sdd/commands/registry.json` can route to governed skills (not direct CLI commands).

## Active Governed Skills

Resolve from `.sdd/skills/registry.json`:

- `sdd-ask`
- `sdd-compress-context`
- `sdd-converge`
- `sdd-correct`
- `sdd-diagnose`
- `sdd-review-architecture`
- `sdd-stabilize`
- `sdd-validate-governance`

For each skill, load its canonical contract before use:
`.sdd/skills/<skill-name>/skill.yaml`

## Mandatory Protocols

1. **Governance Footer**: Every response generated while operating under this skill MUST end with the following compact footer:
   `SDD GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`
   *(Replace ${status} and ${profile} with actual values from `sdd runtime status`)*

2. **Safe Discovery**:
   - Always prefer `sdd runtime status` to check if the runtime is initialized.
   - Use `sdd organize` to pre-index large/noisy input.
   - Use `sdd ask-full` for operational state queries (with heuristic organize step when needed).
   - Refer to `.sdd/source/*` for human-readable policy context.

3. **PEP 723 Execution**:
   - Always execute CLI commands via `uv run sdd` or `make <target>` to ensure environment parity.

## Core Commands Reference

- `sdd runtime status`: Check health of the governance engine.
- `sdd governance validate`: Verify integrity of compiled artifacts.
- `sdd organize "<context>"`: Build indexed intake artifact for selective retrieval.
- `sdd ask "<query>"`: Governed context query (minimal mode).
- `sdd ask-full "<query>"`: Governed context query with full telemetry mode.
- `sdd tools list`: Discover maintenance utilities.
