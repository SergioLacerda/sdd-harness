# Makefile Command Contract

Date: 2026-05-16

## Objective

Keep Makefile targets deterministic and compatible with governed execution policy.

## Rules

- Do not use inline Python execution in Makefile (`python -c ...`).
- Do not use inline shell command payloads (`sh -c ...`, `bash -c ...`).
- Keep Makefile as an orchestrator only; move logic to versioned scripts.
- Critical targets must route through `tools/maintenance/make_tasks.py`:
  - `lint`
  - `lint-fix`
  - `test`
  - `release-dry-run`
  - `clean`

`release-dry-run` uses functional test validation without coverage gate
(`--no-coverage`) to avoid blocking release checks on baseline coverage debt.

## Execution Policy

- Scripts that spawn subprocesses must use `SafeProcessRunner`.
- Pure filesystem tasks may run directly without subprocess usage.
- Any exception to these rules must be explicitly documented and covered by tests.

## Guardrails

- `tests/unit/test_makefile_guardrails.py` blocks fragile inline command patterns.
- `tests/unit/test_make_tasks.py` validates wrapper behavior for release/clean.
