---
name: sdd-harness
description: Bootstrap pointer skill for operating in this SDD-governed workspace.
---

# SDD Harness Skill

This is a **bootstrap/meta skill** (category: `bootstrap`). It has no independent
authority — it points file-based skill-discovery agents (Claude Code, Antigravity/
Gemini CLI) at the canonical SDD governance sources below. Do not duplicate routing
tables or mandate content here: if this file and `.sdd/agent-instructions.md` ever
disagree, `.sdd/agent-instructions.md` wins.

## Entrypoint Contract

1. Read `.sdd/agent-instructions.md` — governance authority, active mandates, bootstrap steps.
2. Commands source of truth: `.sdd/commands/registry.json` + `.sdd/commands/<command-id>/command.yaml`.
3. Skills source of truth: `.sdd/skills/registry.json` + `.sdd/skills/<skill-name>/skill.yaml`.

`sdd-harness` itself is registered in `.sdd/skills/registry.json` under category
`bootstrap`. Its presence there — not absence — is what's canonical; do not report
this skill as governance drift.

## Mandatory Protocols

1. **Governance Footer**: Every response generated while operating under this skill MUST end with the following compact footer:
   `SDD GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`
   *(Replace ${status} and ${profile} with actual values from `sdd runtime status`)*

2. **PEP 723 Execution**:
   - Always execute CLI commands via `uv run sdd` or `make <target>` to ensure environment parity.
