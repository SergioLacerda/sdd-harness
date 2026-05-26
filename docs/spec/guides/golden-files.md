# Golden Files & Contract Tests

**Status: Governance Fixture**
Golden files are the canonical reference for compiled governance artifacts. They are **version controlled** and protected by contract tests.

---

## Philosophy

Golden files follow the **Google/Meta pattern** for snapshot testing:

| Aspect | Principle |
|---|---|
| **Storage** | Git version control (auditable history) |
| **CI behavior** | **Strict**: Fails on divergence, never auto-updates |
| **Updates** | Manual + deliberate (local, code-reviewed, committed) |
| **Failure mode** | Detects accidental changes; forces review of intentional ones |

**Core rule:** If your code changes the compiled artifacts, your tests **must** fail until you update the golden files deliberately.

---

## When Snapshots Diverge

### Symptom: CI Test Failure

```
AssertionError: Compiled artifact diverged from golden file.

If this change is **intentional** (schema/logic update):
  python tools/testing/update-golden-snapshots.py governance

If this change is **accidental**:
  → Check GovernanceOrchestrator and source docs for unexpected changes
```

### Root Causes

1. ✅ **Intentional** — You changed governance logic, mandates, or compiler
   - Run: `make update-golden-snapshots`
   - Review the diff: `git diff tests/contract/fixtures/`
   - Commit together with your logic change

2. ❌ **Accidental** — Your changes unintentionally altered compiled output
   - Revert changes or fix the logic
   - Do NOT update snapshots as a shortcut

---

## Workflow: Update Golden Files

### Step 1: Make Your Changes

```bash
# Edit governance specs, compiler logic, etc.
vim docs/spec/canonical/core/mandates/M001.md
vim packages/core/sdd_compiler/src/...
```

### Step 2: Compile & Test

```bash
make check
# or
pytest tests contracts --tb=short
```

### Step 3a: If Intentional → Update

```bash
make update-golden-snapshots
```

Outputs:

```
✓ Updated: tests/contract/fixtures/governance_core.golden.json
```

### Step 3b: Review the Diff

```bash
git diff tests/contract/fixtures/
```

Look for:

- ✅ Expected changes (new items, updated metadata, version bumps)
- ❌ Unexpected changes (dropped fields, broken structure)

### Step 4: Commit Together

```bash
git add docs/spec/canonical/core/mandates/M001.md \
         packages/core/sdd_compiler/src/... \
         tests/contract/fixtures/governance_core.golden.json

git commit -m "feat: Update governance mandates + golden files

Updated M001 mandate definition. Compiled artifact changed due to:
- New metadata field: category
- Updated rationale text

Golden file updated to reflect new schema."
```

---

## Protection Against Silent Failures

### Why "No Auto-Update in CI"

❌ **Bad (hides failures):**

```yaml
- Run: make update-golden-snapshots  # In CI ← NEVER DO THIS
- Run: make check                    # Always passes (useless)
```

✅ **Good (detects issues):**

```yaml
- Run: make check  # Fails if divergence → forces local action
```

### Audit Trail

Every golden file change is:

1. **Visible in git** — full diff of what changed
2. **Tied to code** — same commit as logic change
3. **Code-reviewed** — PR must approve both logic + fixtures
4. **Versionable** — CI records which commit changed contracts

---

## CI Behavior

### Health Check Workflow (`health.yml`)

1. Compile governance artifacts
2. **Validate determinism** (fingerprints match)
3. **Run contract tests** ← **Fails if golden mismatch**
4. Report divergence (if any)

### What CI Will NOT Do

- ❌ Auto-commit golden file updates
- ❌ Accept divergence silently
- ❌ Allow passing without snapshot sync

---

## Troubleshooting

### "Golden file is outdated in main"

This means someone committed logic changes without updating snapshots.

```bash
# Pull latest
git pull origin main

# Update locally
make update-golden-snapshots

# Create a follow-up fix commit
git add tests/contract/fixtures/
git commit -m "fix: Sync golden files with main

Updated golden files to match latest compiled artifacts from main."

# Push
git push origin fix/golden-sync
```

### "I changed something small, why did golden change so much?"

Check:

- Did you update `docs/spec/canonical/` (mandates, policies)?
- Did you touch compiler logic?
- Did you change version scheme?

Any of these triggers recompilation. Review carefully:

```bash
# See full diff with context
git diff -U10 tests/contract/fixtures/governance_core.golden.json
```

### "My CI still fails even after updating"

Golden files are cached. Try:

```bash
make clean
make update-golden-snapshots
make check
```

---

## Commands Reference

| Command | Purpose |
|---|---|
| `make check` | Run all tests (fails if golden diverges) |
| `make update-golden-snapshots` | Update all golden files |
| `python tools/testing/update-golden-snapshots.py governance` | Update only governance snapshots |

---

## See Also

- [Security Policy](../reference/SECURITY.md) — Security practices for governance artifacts
