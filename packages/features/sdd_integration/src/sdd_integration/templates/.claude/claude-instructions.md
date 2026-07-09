# Claude — SDD Governance Bootstrap
<!-- Governance fingerprint: {FINGERPRINT} -->
<!-- Drift check: fingerprint must match .sdd/metadata.json → governance_fingerprint -->

You are operating in a workspace governed by **Spec Driven Development (SDD)**.

## Critical Instruction

Read and adhere to the canonical governance rules in:
```
.sdd/agent-instructions.md
```

This file is the **single source of truth** for all governance policies in this workspace.

## Quick Reference

- **Mandate enforcement**: Non-negotiable rules — see `.sdd/source/mandates/mandates.md`
- **Governance status**: Run `sdd runtime status` to check workspace health
- **Validation**: Run `sdd governance validate` before commits
- **Activation**: Governance activates automatically on project load via `.sdd/seedlings/`

## For Questions

All governance documentation lives in `.sdd/source/`:
- `mandates/mandates.md` — Mandate descriptions and enforcement rules
- `guidelines/` — Customizable guidelines by category
- `README.md` — Onboarding guide for agents

## Safe Fallback

If `.sdd/` is missing or incomplete, do not proceed — ask the human to run `sdd wizard`
to regenerate the governance template.
