---
name: sdd-harness
description: Expert skill for operating the SDD (Sovereign Digital Design) Governance Runtime and CLI.
---

# SDD Harness Skill

This skill provides the operational protocols for interacting with the SDD Governance Runtime. Use this skill when managing governance, auditing compliance, or performing system diagnostics.

## Operational Modes (Templates)

The following prompt templates in `.github/prompts/` define the standard operating procedures:

| Template | Purpose | When to use |
|---|---|---|
| `sdd-ask.prompt.md` | Context Query | When querying the AI for governance-specific knowledge. |
| `sdd-ask-full.prompt.md` | Context Query (Full) | When full telemetry and richer state extraction are required. |
| `sdd-organize.prompt.md` | Context Preparation | When input/logs are large and require indexed pre-organization. |
| `sdd-diagnose.prompt.md` | Runtime Diagnosis | When diagnosing workspace/runtime issues. |
| `sdd-validate-governance.prompt.md` | Governance Preflight | Before governed operations requiring integrity checks. |
| `sdd-stabilize.prompt.md` | Stabilization | Before handoff to ensure controlled operational state. |
| `sdd-compress-context.prompt.md` | Token Economy | Reduce context footprint while preserving governance context. |
| `sdd-review-architecture.prompt.md` | Architecture Review | Evaluate architecture alignment with mandates. |
| `sdd-correct.prompt.md` | Targeted Correction | Apply minimal correction to a specific governance violation. |
| `sdd-converge.prompt.md` | Convergence | Drive systemic alignment after targeted corrections. |

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
- `sdd tools list`: Discover maintenance utilities.
- `sdd metrics summary`: Review recent compliance events.
