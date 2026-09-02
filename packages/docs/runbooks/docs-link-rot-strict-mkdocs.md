# Docs Link Rot Strict MkDocs

Verification state: documented

## Symptoms

- `mkdocs build --strict` fails on a relative link.
- A docs page links into `.analysis/` and the strict build cannot resolve it.
- ADR or runbook links point to files that were renamed or never created.
- Link validation reports stale references after docs reorganization.

## Diagnosis

1. Run the strict docs build through the normal target:

   ```bash
   make docs-build
   ```

2. Read the first failing link error.
3. Determine whether the target is:
   - inside the published `docs/` tree;
   - outside the published tree, such as `.analysis/`;
   - a stale renamed file;
   - a planned runbook stub that was never written.
4. For `.analysis/` references, prefer plain text paths instead of Markdown links.

## Resolution Steps

1. Fix links that should resolve inside `docs/`.
2. Convert non-published evidence paths to plain text.
3. Remove or replace links to nonexistent stubs.
4. Re-run:

   ```bash
   make docs-build
   make docs-link-check
   ```

## Rollback

1. Revert the doc reorganization or link update that introduced unresolved links.
2. Re-run the strict build.

## Post-Incident

- Add missing runbooks as real files before linking them.
- Update navigation indexes when moving docs.

## Evidence To Attach

- strict MkDocs error output
- changed links
- `make docs-build` output after the fix

## Sources

- `docs/spec/decisions/2026-05-24-docs-link-rot-cleanup-design.md`
- `docs/maintenance/landing-site-runbook.md`
