# GitHub Pages Publish Checklist

Use this checklist when docs workflows are green but the site was not updated.

## 1) Repository settings

1. GitHub repository has **Pages** enabled.
2. Pages source is set to **GitHub Actions**.
3. Repository variable `ENABLE_GITHUB_PAGES` is set to `true`.

## 2) Trigger conditions in `docs.yml`

Publish only runs when all conditions are true:

1. Event is `push`.
2. Branch is `main`.
3. `vars.ENABLE_GITHUB_PAGES == 'true'`.

Reference: `.github/workflows/docs.yml`.

## 3) Required file-change paths

The workflow triggers on changes in:

- `docs/**`
- `mkdocs.yml`
- `README.md`
- docs validation scripts under `tools/`
- `.github/workflows/docs.yml`

If your commit does not touch these paths, docs workflow will not run.

## 4) Fast local verification

```bash
uv run mkdocs build --strict
```

If this fails locally, fix docs before expecting publish.

## 5) CI verification

In GitHub Actions:

1. `docs-quality` must pass.
2. `Upload Pages artifact` step must run (not skipped).
3. `deploy` job must run and succeed.

If `deploy` is skipped, the most common cause is `ENABLE_GITHUB_PAGES` not set to `true`.
