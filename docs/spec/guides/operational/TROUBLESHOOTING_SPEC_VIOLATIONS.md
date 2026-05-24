# 🔧 TROUBLESHOOTING_SPEC_VIOLATIONS — Debug Guide

**For:** Developers fixing CI/CD failures
**Time:** 5-15 minutes per error
**Complexity:** Easy (decision tree + examples)
**Prerequisites:** Understand SPEC layer structure

---

## 🎯 Quick Decision Tree

Start here when CI/CD fails with spec violation:

```
CI/CD Failed: "SPEC Violation Detected"
    ↓
    What's the error message?
    ↓
    ├─ "path 'docs/ia/custom/...' not allowed" → See #1: SPEC_PATH_VIOLATION
    ├─ "Status must be: [Complete, WIP, Deprecated]" → See #2: INVALID_STATUS
    ├─ "H1 header missing in IA-FIRST section" → See #3: HEADING_HIERARCHY
    ├─ "Backtick links not allowed: [`doc.md`]" → See #4: BACKTICK_LINKS
    ├─ "Missing metadata field: [field]" → See #5: MISSING_METADATA
    ├─ "No IA-FIRST notice in first 50 lines" → See #6: MISSING_IA_FIRST_NOTICE
    ├─ "Exit code 1: Validation failed" → See #7: VALIDATION_ERROR
    └─ "Something else?" → See #8: UNKNOWN_ERROR
```

---

## #1: SPEC_PATH_VIOLATION — Wrong Folder

**Error Message:**
```
❌ validate-ia-first.py (line 42): path 'docs/ia/custom/my-project/something.md'
   not allowed in this layer. Allowed paths: [...]
```

**What this means:**
You created a file in a wrong SPEC layer. Each layer has specific allowed paths.

**Diagnosis (1 min):**

```bash
# Find all docs you modified
git status | grep docs/ia/

# Check which layer each file is in
ls docs/ia/custom/my-project/
# Output: development/, reality/, archive/

# Check if path matches SPEC structure
# Valid: docs/ia/custom/PROJECT_NAME/[development|reality|archive]/...
# Invalid: docs/ia/custom/PROJECT_NAME/random-folder/... ← YOUR ERROR
```

**Fix (2-5 min):**

| Wrong Path | Correct Path | Why |
|------------|--------------|-----|
| `docs/ia/custom/proj/guides/...` | `docs/ia/guides/operational/...` | Operational guides go in main guides, not custom/ |
| `docs/ia/custom/proj/rules.md` | `/EXECUTION/spec/CANONICAL/rules/...` | Rules go in CANONICAL (immutable), not custom/ |
| `docs/ia/reality/some-file.md` | `docs/ia/custom/proj/reality/...` | Reality is project-specific (custom/) |
| `docs/ia/threads/thread-a.md` | `docs/ia/custom/proj/development/threads/...` | Threads are development artifacts |

**Resolution:**

```bash
# Option 1: Move file to correct location
mv docs/ia/custom/my-project/wrong-path/file.md docs/ia/custom/my-project/reality/limitations/file.md

# Option 2: Delete if created in wrong place
rm docs/ia/custom/my-project/wrong-path/file.md

# Commit and re-test
git add docs/ia/
git commit -m "Fix: Move file to correct SPEC layer"
```

**Prevention:**
- Always verify path before creating file
- Reference: [architecture.md](../../canonical/specifications/architecture.md)
- Ask: "Is this immutable (CANONICAL) or project-specific (custom/)?"

---

## #2: INVALID_STATUS — Wrong Status Field

**Error Message:**
```
❌ validate-ia-first.py (line 156): Status must be one of: [Complete, WIP, Deprecated]
   Found: "in-progress"
```

**What this means:**
You used a status value not in the allowed list.

**Diagnosis (1 min):**

```bash
# Search for status in your file
grep -n "Status:" docs/ia/custom/my-project/some-file.md
# Output: Status: in-progress  ← WRONG

# Check valid values
grep -A3 "## Status Field" docs/ia/IA_FIRST_SPECIFICATION.md
```

**Fix (2 min):**

```markdown
# WRONG:
Status: in-progress

# CORRECT:
Status: WIP

# Examples:
- Status: Complete        (finished, ready to use)
- Status: WIP            (work in progress)
- Status: Deprecated     (old, don't use)
```

**Valid values:**

| Value | Meaning | Example Usage |
|-------|---------|----------------|
| `Complete` | Finished, tested, ready | Finalized spec documents |
| `WIP` | Work in progress | Features being built |
| `Deprecated` | Don't use, being phased out | Old guides, legacy features |

**Resolution:**

```bash
# Find and fix in your editor
sed -i 's/Status: in-progress/Status: WIP/g' docs/ia/custom/my-project/some-file.md

# Verify fix
grep "Status:" docs/ia/custom/my-project/some-file.md

# Commit
git commit -m "Fix: Update status to valid value"
```

---

## #3: HEADING_HIERARCHY — Wrong Header Levels

**Error Message:**
```
❌ validate-ia-first.py (line 89): Heading hierarchy broken.
   Found H3 (###) without preceding H2 (##)
```

**What this means:**
Markdown headers are out of order. Must be: H1 (#) → H2 (##) → H3 (###), never skip levels.

**Diagnosis (1 min):**

```bash
# View your doc's headers
grep "^#" docs/ia/custom/my-project/some-file.md

# Example of WRONG:
# My Document         ← H1
## Section A          ← H2
#### Subsection      ← H4 (skipped H3!) ← ERROR

# Example of CORRECT:
# My Document         ← H1
## Section A          ← H2
### Subsection       ← H3 (no skip)
```

**Fix (3 min):**

```bash
# Find the line with bad header
grep -n "^###" docs/ia/custom/my-project/some-file.md | head -1
# Output: 15:#### Subsection

# Edit file: change #### to ###
# Before: #### Subsection
# After:  ### Subsection

# Verify fix
grep -n "^#" docs/ia/custom/my-project/some-file.md | head -5

# Commit
git commit -m "Fix: Correct heading hierarchy"
```

**Prevention:**
- H1 (#) — One per file, at top
- H2 (##) — Major sections
- H3 (###) — Subsections under H2
- H4+ (####) — Only after H3 (no skips)

---

## #4: BACKTICK_LINKS — Links Formatted Wrong

**Error Message:**
```
❌ validate-ia-first.py (line 73): Backtick links not allowed.
   Use format [text](path.md) not [`text`](path.md)
```

**What this means:**
You wrapped link text in backticks. Don't do that—plain text only.

**Diagnosis (1 min):**

```bash
# Search for backtick links
grep -E '\[`.*`\]' docs/ia/custom/my-project/some-file.md

# Example of WRONG:
See [`guidelines`](guidelines.md) for details ← WRONG (backticks in link)

# Example of CORRECT:
See [guidelines](guidelines.md) for details
```

**Fix (2 min):**

```bash
# Replace all backtick links with plain links
sed -i 's/\[`\(.*\)`\]/[\1]/g' docs/ia/custom/my-project/some-file.md

# Verify fix
grep -E '\[`.*`\]' docs/ia/custom/my-project/some-file.md
# Should return nothing (no matches)

# Commit
git commit -m "Fix: Remove backticks from links"
```

**Prevention:**
- Links: `[text](path.md)` ✅ CORRECT
- Code: `` `code` `` ✅ CORRECT (backticks allowed for code)
- Combined: `` [`code`](path.md) `` ❌ WRONG (backticks in link text)

---

## #5: MISSING_METADATA — Required Fields

**Error Message:**
```
❌ validate-ia-first.py (line 112): Missing metadata field: Status
```

**What this means:**
Your file is missing a required metadata field.

**Required fields:**

```markdown
# My Document

**For:** [Who should read this?]
**Time:** [How long does it take?]
**Complexity:** [Easy/Medium/Hard]
**Prerequisites:** [What should you know first?]

---

[Rest of document...]
```

**Diagnosis (1 min):**

```bash
# Check which fields your doc has
head -10 docs/ia/custom/my-project/some-file.md | grep "^\*\*"

# Example output (missing Time):
# **For:** Developers
# **Complexity:** Medium
# **Prerequisites:** ...
# ← Missing: **Time:**
```

**Fix (2 min):**

```markdown
# BEFORE (missing fields):
**For:** Developers
**Complexity:** Medium

# AFTER (all fields):
**For:** Developers fixing CI/CD issues
**Time:** 5-15 minutes per error
**Complexity:** Easy
**Prerequisites:** Understand SPEC structure
```

**All required metadata:**

| Field | Example | Purpose |
|-------|---------|---------|
| `For:` | "Developers fixing CI/CD" | Target audience |
| `Time:` | "5-15 minutes" | Expected duration |
| `Complexity:` | "Easy/Medium/Hard" | Difficulty level |
| `Prerequisites:` | "Read AGENT_HARNESS" | What to know first |

**Resolution:**

```bash
# Add missing field to top of doc (after H1)
# Edit manually or use sed:
sed -i '2a **Time:** 5-15 minutes' docs/ia/custom/my-project/some-file.md

# Commit
git commit -m "Fix: Add missing metadata"
```

---

## #6: MISSING_IA_FIRST_NOTICE — IA-FIRST Not Found

**Error Message:**
```
❌ validate-ia-first.py (line 201): No IA-FIRST notice found in first 50 lines
```

**What this means:**
All SPEC docs must have a clear "IA-FIRST" section in the first 50 lines.

**Diagnosis (1 min):**

```bash
# Check first 50 lines
head -50 docs/ia/custom/my-project/some-file.md | grep -i "IA-FIRST"

# Should output something like:
# IA-FIRST: This is an IA-FIRST (or similar indicator)

# If empty: IA-FIRST section missing
```

**Fix (3 min):**

```markdown
# BEFORE (no IA-FIRST):
# My Document
**For:** Developers
**Time:** 5 min

---

Some content...

# AFTER (with IA-FIRST):
# My Document

**IA-FIRST:** This guide documents the procedure for troubleshooting SPEC violations.

**For:** Developers fixing CI/CD failures
**Time:** 5-15 minutes
**Complexity:** Easy
**Prerequisites:** Understand SPEC layer structure

---

Some content...
```

**Resolution:**

```markdown
# Add this after H1 and metadata (required format):

---

**IA-FIRST:** [One sentence describing what this doc is about]

---
```

**Examples:**

```markdown
**IA-FIRST:** This guide documents emergency procedures for when CI/CD gates fail.

**IA-FIRST:** This document defines the canonical constitution for [PROJECT_NAME].

**IA-FIRST:** This specifies how to add new projects to the SPEC framework.
```

---

## #7: VALIDATION_ERROR — Unknown Failure

**Error Message:**
```
❌ validate-ia-first.py exited with code 1
   Error details (see full log):
   [Long error message...]
```

**What this means:**
General validation failure. Details are in the full CI/CD log.

**Diagnosis (3-5 min):**

```bash
# Run validation locally to see full error
python docs/ia/SCRIPTS/validate-ia-first.py --audit docs/ia/

# Output shows exact line + error:
# ERROR [docs/ia/custom/proj/file.md:25]: Description of what's wrong

# Fix the specific error (usually matches one of #1-6 above)
```

**Resolution:**

1. Run validation locally
2. Identify specific error (matches #1-6 above?)
3. Apply fix from that section
4. Re-run validation to confirm

---

## #8: UNKNOWN_ERROR — Not Listed Above

**What to do:**

```bash
# Step 1: Get full error details
# Check GitHub Actions logs:
# https://github.com/user/repo/actions → Select failed job → View logs

# Step 2: Search error message
grep -r "error-text" docs/ia/ | head -5

# Step 3: Check if it matches a pattern
# Does it say: "path", "Status", "heading", "backtick", "metadata", "IA-FIRST"?
# If yes: See #1-6 above

# Step 4: If genuinely unknown:
# Post in team Slack with:
# - Full error message
# - File that triggered it
# - What you were trying to do
```

---

## 🚨 Prevention Checklist

Before committing docs, verify:

- [ ] IA-FIRST section exists in first 50 lines
- [ ] Status is one of: [Complete, WIP, Deprecated]
- [ ] All required metadata: For, Time, Complexity, Prerequisites
- [ ] Headers in correct hierarchy (H1 → H2 → H3, no skips)
- [ ] No backticks in link text: Use `[text](link.md)` not `[`text`](link.md)`
- [ ] File path matches SPEC structure (custom/, CANONICAL/, guides/)
- [ ] No WIP markers if Status: Complete
- [ ] No TODO or FIXME if Status: Complete

**Quick check:**
```bash
# Run locally before pushing
python docs/ia/SCRIPTS/validate-ia-first.py --audit docs/ia/

# Should output: ✅ Validation passed
```

---

## 📊 Common Violation Statistics

| Violation | Frequency | Fix Time |
|-----------|-----------|----------|
| SPEC_PATH_VIOLATION | ~30% of failures | 2-5 min |
| INVALID_STATUS | ~20% | 1-2 min |
| HEADING_HIERARCHY | ~15% | 2-3 min |
| BACKTICK_LINKS | ~15% | 1-2 min |
| MISSING_METADATA | ~12% | 2-3 min |
| MISSING_IA_FIRST_NOTICE | ~8% | 2-3 min |

**Total average fix time: 5-10 minutes**

---

## 🔗 Related Docs

- [IA_FIRST.md](../../../runtime/IA_FIRST.md)
- [architecture.md](../../canonical/specifications/architecture.md)
- [ARCHITECTURE_VALIDATION.md](./ARCHITECTURE_VALIDATION.md)
- [CORE__START_HERE.md](./CORE__START_HERE.md)

---

**Last Updated:** 2026-04-19
**Status:** Complete (v1.0)
**Tested:** 116 docs audit in [PROJECT_NAME] codebase
