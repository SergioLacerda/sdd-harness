# Docs Site Selector Publish

Verification state: documented

## Symptoms

- `/selector/` returns 404 locally or after publishing.
- The landing page links to the selector, but the selector artifact is absent.
- `make docs-serve` fails because `build/site/selector/index.html` is missing.
- CI validates MkDocs but the assembled site is incomplete.

## Diagnosis

1. Confirm the intended publication split:
   - landing app publishes to `/`;
   - MkDocs publishes to `/docs/`;
   - selector publishes to `/selector/`.
2. Run the full docs build:

   ```bash
   make docs-build
   ```

3. Check for the selector artifact:

   ```bash
   test -f build/site/selector/index.html
   ```

4. If serving locally, use:

   ```bash
   make docs-serve
   ```

## Resolution Steps

1. Do not hand-build only MkDocs when investigating selector publication.
2. Re-run the full publication build:

   ```bash
   make docs-build
   ```

3. Fix the failing stage reported by the build: Astro, MkDocs, or selector
   compiler.
4. Re-run `make docs-serve` and verify `/selector/`.

## Rollback

1. Revert the docs/site change that broke the full build.
2. Re-run `make docs-build`.
3. Do not publish until the assembled `build/site/` tree is complete.

## Post-Incident

- Add a failure ledger entry when publication reached CI or production.
- Update this runbook if a new build-stage failure pattern appears.

## Evidence To Attach

- `make docs-build` output
- `make docs-serve` output
- presence or absence of `build/site/selector/index.html`
- failing source file path if known

## Sources

- `docs/maintenance/landing-site-runbook.md`
- `docs/guides/FRONTEND_SELECTOR.md`
- `docs/guides/GITHUB_PAGES_PUBLISH_CHECKLIST.md`
