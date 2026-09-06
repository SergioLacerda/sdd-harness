# Runbook — Verifying Whether a Refined Package Was Actually Implemented

## Symptom / Trigger

A `pending/` or `refined/` package needs to be evaluated for possible
closure to `done/`, or a user asks "was this actually implemented?" for one
or more packages. Guessing from `tasks.md` checkboxes or a Sniper report
existing is explicitly insufficient evidence
(`11-critical-hit.md` § Insufficient Evidence).

## Bounded Verification Procedure

1. **Read the target package's `tasks.md` acceptance_checks and
   implementation_plan** — these define what "done" means for this specific
   package; do not substitute a generic definition.
2. **For each `implementation_handoff` / code-touching task, check the
   declared file(s) exist and match the described shape** — a direct file
   read, not a guess from the task title.
3. **Re-run the package's own stated validation commands** (its declared
   test files, its declared manual dry-run steps) and record the real
   pass/fail result. Do not report a task as validated from memory or from
   the original mission's own claims — re-run it now.
4. **For behavior that can't be validated by an existing test, reproduce it
   directly** where feasible (e.g., invoke the actual function/class in a
   throwaway scratch directory) rather than only reading the code and
   inferring behavior — reading code proves what *should* happen; running it
   proves what *does* happen.
5. **Classify each task individually**, not the package as a whole in one
   guess: done-and-verified / not-done / done-but-unconfirmed (state exactly
   why it's unconfirmed).
6. **If verification is genuinely ambiguous** — the acceptance checks can't
   be confidently confirmed against real command output or current file
   content — stop and say so. Do not force a verdict.
7. **Classify the overall package**: `implemented` only if every task
   verifies; `partially_implemented` if some do and some don't (list which);
   `not_implemented` if none do.
8. **Only a package with zero declared residual work is a Critical Hit
   closure candidate** — partial implementation, even 90% done, blocks
   closure per `11-critical-hit.md`'s explicit disqualifier.
9. **Write the completion report / evaluation artifact citing the specific
   evidence per claim** (file paths, command output, reproduction steps) —
   never "it looks done" without a cited command or file read backing it.

## Expected Outputs

- Per-task verdict with cited evidence (not a single package-level guess).
- An explicit list of residual/gap items, if any.
- A recommendation: close via Critical Hit (only if zero residuals), or
  generate a residual refined package for the gaps (via Archivist), or
  report `not_implemented` outright.

## Stop Conditions

- Evidence is ambiguous and cannot be resolved by re-running an existing,
  declared validation command or a direct reproduction within this
  procedure's bound — stop, do not guess.
- The package's own `tasks.md`/acceptance_checks are missing or malformed —
  stop, this procedure requires them as the definition of "done."

## Source

Distilled from `.analysis/refined/20260906-refined-packages-evaluation/`'s
own evaluation of `20260825-changelog-readme-automation` and
`20260825-standalone-init-def` — see that mission's archived `analysis.md`
(`.analysis/done/20260906-refined-packages-evaluation/analysis.md`) for a
worked example of every step above applied to two real packages.
