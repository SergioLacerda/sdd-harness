# GitHub Copilot Governance Bootstrap

This workspace uses SDD governance. Treat this file as the first bootstrap for Copilot sessions.

## Required Startup Order

1. Read `.spec.config` and resolve `spec_path`.
2. Read the framework entry point at `.../EXECUTION/_START_HERE.md`.
3. Read the mandatory rules in `.../EXECUTION/spec/CANONICAL/rules/constitution.md` and `.../EXECUTION/spec/CANONICAL/rules/ia-rules.md`.
4. Follow `.../EXECUTION/spec/guides/onboarding/AGENT_HARNESS.md` before making substantive changes.

## Workspace Governance Inputs

- Mandatory mandates live in `.sdd/source/mandates/mandates.md`
- Active guidelines live in `.sdd/source/guidelines/`
- Project metadata and fingerprints live in `.sdd/metadata.json`
- Runtime health is tracked by `sdd runtime status`

## Operating Rules

- Do not bypass mandatory mandates.
- Prefer generated templates and canonical specifications over improvised structure.
- Run `sdd governance validate` before finalizing a change.
- When the workspace state is unclear, run `sdd runtime status` first.

## Expected Validation Commands

```bash
sdd governance validate
sdd runtime status
```

## Notes

This template is exported by the wizard as bootstrap guidance. The generated project can later replace it with compiled, fingerprint-aware instructions.
