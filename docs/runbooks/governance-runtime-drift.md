# Governance Runtime Drift

Verification state: documented

## Symptoms

- `.sdd/` runtime files disagree with authored docs.
- Governance validation reports stale or mismatched generated output.
- Agents cite `.sdd/` behavior that no longer matches `docs/`.
- A generated seed or runtime file appears to be the only place a rule exists.

## Diagnosis

1. Read `docs/governance-runtime-model.md`.
2. Identify the authored source in `docs/spec/canonical/governance-sources.yaml`.
3. Compare the source entry's declared outputs with the generated `.sdd/` files.
4. Check runtime health:

   ```bash
   uv run sdd runtime status --force
   uv run sdd governance validate
   ```

5. Treat disagreement between registry outputs and `.sdd/` as build drift, not as
   permission to edit `.sdd/` directly.

## Resolution Steps

1. Fix the authored source under `docs/`.
2. Regenerate runtime outputs:

   ```bash
   uv run sdd governance generate --full-bootstrap
   ```

3. Re-run validation:

   ```bash
   uv run sdd governance validate
   uv run sdd runtime status --force
   ```

4. If the change affects agent entrypoints, regenerate skills/seeds as required by
   the specific task.

## Rollback

1. Revert the authored `docs/` source change.
2. Regenerate `.sdd/` from the restored source.
3. Re-run governance validation.

## Post-Incident

- Record the drift class and root cause in `docs/incidents/FAILURE_LEDGER.md` when
  this was a real incident.
- Update the relevant source registry entry if the output mapping was wrong.

## Evidence To Attach

- `git diff -- docs/`
- `uv run sdd governance validate` output
- `uv run sdd runtime status --force` output
- source registry entry from `docs/spec/canonical/governance-sources.yaml`

## Sources

- `docs/governance-runtime-model.md`
- `docs/guides/CONVERGENCE.md`
- `docs/incidents/PLAYBOOKS.md`
- `docs/cognition/context-loading/context_flow.md`
