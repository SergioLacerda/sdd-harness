# Docs Link Rot Cleanup + CI Link Check

**Date:** 2026-05-24
**Status:** Approved

## Problem

184 broken internal links across 220 markdown files. Dominant cause: a past migration from
`docs/spec/canonical/` structure to the current `/docs/spec/` structure left references
un-updated. Secondary causes: ADR filenames changed after initial reference, runbook stubs
referenced but never created.

Without a CI gate, link rot will silently re-accumulate.

## Goals

- Reduce broken internal links to zero.
- For links with no resolvable target: remove or create the missing content.
- Prevent future link rot via a CI check on every PR.

## Non-Goals

- Changing document content beyond link targets.
- Restructuring the docs tree.
- Fixing external (HTTP) links.

---

## Design

### Phase 1 — Automated Classification Script

A Python script `tools/docs/check_links.py` scans all `.md` files and classifies every
internal link into one of three buckets:

| Bucket | Criteria | Action |
|---|---|---|
| `auto-fixable` | Broken link has a clear pattern mapping to an existing file | Auto-correct |
| `orphan` | No valid target exists and content is not needed | Remove link + inline note |
| `needs-creation` | No valid target exists but content is genuinely required | Flag for creation |

The script is re-used as the CI check (same binary, different exit behavior).

**Known migration mappings (auto-fixable patterns):**

| Old pattern | Resolves to |
|---|---|
| `docs/spec/canonical/` | `/docs/spec/canonical/` |
| `docs/spec/` | `/docs/spec/` |
| `spec/guides/operational/CORE__START_HERE.md` | `spec/guides/operational/CORE__START_HERE.md` |
| `spec/canonical/` | `spec/canonical/` |
| `spec/guides/integration/` | `spec/guides/integration/` |
| `spec/decisions/ADR-001-clean-architecture-8-layer.md` | `spec/decisions/ADR-001-clean-architecture-8-layer.md` |
| (other short ADR names) | Full filename resolved by prefix match |

**Script output modes:**

```
check_links.py --mode audit     # prints classification report, exit 0
check_links.py --mode fix       # applies auto-fixable mappings in place
check_links.py --mode ci        # prints broken links, exit 1 if any found
```

### Phase 2 — Batch Fix (auto-fixable)

Run `check_links.py --mode fix`. Applies all pattern-mapped corrections in one pass.
No manual review needed for this bucket — mappings are deterministic.

### Phase 3 — Orphan Triage

For links classified as `orphan`, the script outputs a triage report:

```
ORPHAN: docs/spec/guides/operational/MONITORING.md:142
  Link: ./runbooks/vector-search-down.md
  Target: does not exist
  Suggested action: [remove | create]
```

A human reviews the report and decides per entry. Execution options:

- **Remove**: delete the link and add a `> Note: runbook not yet written.` inline.
- **Create**: add the file to the `needs-creation` list.

### Phase 4 — Create Missing Content

For entries confirmed as `needs-creation`, create stub files with the IA First schema:

```markdown
# {Title}

> Status: stub — content required.

## Purpose
## Steps
## Escalation
```

Stub files satisfy the link (no more broken reference) and signal explicitly that content
is incomplete, unlike a missing file which fails silently.

### Phase 5 — CI Link Check

A new step added to the existing `reusable-test.yml` (runs on every PR):

```yaml
- name: Check internal doc links
  shell: bash
  run: uv run python tools/docs/check_links.py --mode ci
```

Exit behavior:

- Exit 0: all internal links resolve to existing files.
- Exit 1: one or more broken links found; output lists file, line, and broken target.

The check runs only on `.md` files under `docs/`. It does not check external URLs.

---

## Script Design (`tools/docs/check_links.py`)

```
Input:  docs/ tree (all .md files)
Output: classified link report

Algorithm:
  for each .md file:
    extract all [text](target) where target starts with ./ or ../
    for each target:
      resolve absolute path relative to file location
      if path exists → skip (valid)
      else:
        attempt pattern mappings → auto-fixable
        if no mapping → orphan or needs-creation
```

**Scope:** Internal relative links only (`./`, `../`). Absolute paths and HTTP links excluded.

**Cross-platform:** Uses `pathlib.Path` — no shell-specific behavior.

---

## Files Affected

| File | Change |
|---|---|
| `tools/docs/check_links.py` | New — link scanner/fixer/CI check |
| `docs/**/*.md` (up to 220 files) | Links corrected in Phase 2 and 3 |
| Missing runbook stubs | Created in Phase 4 |
| `.github/workflows/reusable-test.yml` | Add CI link check step |

---

## Acceptance Criteria

1. `check_links.py --mode ci` exits 0 on the full `docs/` tree after cleanup.
2. All auto-fixable links corrected without manual intervention.
3. All orphan links either removed or replaced with creation stubs.
4. CI step blocks PRs that introduce new broken internal links.
5. Script works on Linux and Windows (`pathlib` only, no `grep`/`find`).
