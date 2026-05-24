# 📤 MIGRATING_DOCS_BETWEEN_PROJECTS — Safe Movement Guide

**For:** Architects moving docs from custom/ to CANONICAL (or vice versa)
**Time:** 20-30 minutes per doc
**Complexity:** High (impacts all projects)
**Prerequisites:** Understand SPEC layers + multi-project coordination

---

## 🎯 Quick Overview

**When to migrate:**
- Custom doc proven stable across 2+ projects → Move to CANONICAL
- CANONICAL rule too specific to one project → Move to custom/PROJECT/
- Policy change requires all projects to adopt new rule → Move to CANONICAL

**When NOT to migrate:**
- Doc not yet tested with multiple projects → Keep in custom/
- Project-specific constraint (campaign size, etc.) → Keep in custom/
- Temporary/experimental → Keep in development/

---

## 📊 Decision Matrix

**Should this doc be in CANONICAL?**

```
Question 1: Does this apply to ALL projects?
  YES → Continue to Q2
  NO  → Keep in custom/PROJECT/ (STOP)

Question 2: Is it proven stable in 2+ projects?
  YES → Continue to Q3
  NO  → Keep in custom/ (STOP)

Question 3: Would removing it cause problems?
  YES → Needs backwards compatibility layer
  NO  → Safe to move (PROCEED)

Result: This doc is ready for CANONICAL migration
```

**Examples:**

```
✅ MIGRATE to CANONICAL:
   - "All projects use Python 3.10+"  (applies everywhere)
   - "All projects follow clean architecture" (proven pattern)
   - "Thread isolation mandatory" (core governance)

❌ KEEP in custom/:
   - "[Project A] uses max 50 concurrent entities" (project-specific)
   - "[Project B] prioritizes performance for [domain]" (domain-specific)
   - "Experimental: new logging framework" (not yet stable)
```

---

## 🔄 Migration Process (7 Steps)

### Step 1: Prepare Source Doc (2 min)

**Location:** `docs/ia/custom/PROJECT/reality/something.md`

**Update header to indicate migration:**

```markdown
# Original Title

**Status:** Complete
**Version:** 1.0
**Stability:** Proven in 2+ projects ← Add this line

---

IA-FIRST section...
Rest of document...
```

**Add reference section at bottom:**

```markdown
---

## 📝 Version History

- **v1.0 (date):** Initial in custom/[PROJECT_NAME]/
- **v1.1 (date):** Tested in additional project, ready for CANONICAL

---

**Migration scheduled for:** 2026-04-20
**Approval:** [Team lead sign-off]
```

### Step 2: Review for Project-Specific Content (3 min)

```bash
# Search for project-specific references
grep -i "rpg-narrative\|campaign\|project-specific" \
  docs/ia/custom/PROJECT/reality/something.md

# If found, extract project-specific parts into separate doc
# BEFORE (mixed):
# "[PROJECT_NAME] uses 50 concurrent campaigns, which means..."

# AFTER (generic in CANONICAL):
# "Projects typically use 50-200 concurrent entities, which means..."

# AFTER (project-specific in custom/):
# "[PROJECT_NAME] constraint: max 50 concurrent campaigns"
```

**Generic version checklist:**

- [ ] Removes project name from examples
- [ ] Replaces "campaign" with "entity" or "primary domain object"
- [ ] Removes performance targets specific to one project
- [ ] Uses inclusive language ("projects often" instead of "we always")

### Step 3: Determine CANONICAL Layer (2 min)

**Where does it belong in CANONICAL?**

```
Question: What type of document is this?

RULES (mandatory enforcement)
  → /EXECUTION/spec/CANONICAL/rules/ia-rules.md (or update existing)

DECISIONS (architectural choices)
  → /EXECUTION/spec/CANONICAL/decisions/ADR-*.md (new ADR)

SPECIFICATIONS (how to implement)
  → /EXECUTION/spec/CANONICAL/specifications/architecture.md (or relevant spec)

PROCEDURES (how to do something)
  → docs/ia/guides/operational/PROCEDURE_NAME.md

SECURITY (security constraints)
  → /EXECUTION/spec/CANONICAL/specifications/security-model.md

ARCHITECTURE (layer definitions)
  → /EXECUTION/spec/CANONICAL/specifications/architecture.md
```

**Decision matrix:**

```
Document type: "Max concurrent entities constraints"
  ↓
Is it a rule? NO (informational)
Is it a decision? YES (architectural choice for scalability)
  ↓
Create: /EXECUTION/spec/CANONICAL/decisions/ADR-007-concurrent-entity-constraints.md
```

### Step 4: Create CANONICAL Version (5 min)

**Create new file in CANONICAL:**

```markdown
# New Title (Genericized)

**IA-FIRST:** [Description of what this rule/spec/procedure is]

**For:** [All projects | Teams adding projects | Architects]
**Time:** [5 min read]
**Complexity:** Medium
**Prerequisites:** [What to know first]

---

## Overview

[Generalized version of the content]

---

## Application to All Projects

This rule applies universally:
- Project A: [how it applies]
- Project B: [how it applies]
- Future projects: [guideline for application]

---

## Project Specializations

Individual projects may specialize this rule:
- See: docs/ia/custom/PROJECT_A/SPECIALIZATIONS/constitution-*.md
- See: docs/ia/custom/PROJECT_B/SPECIALIZATIONS/constitution-*.md

---

## Related Docs

- [ADDING_NEW_PROJECT.md](./ADDING_NEW_PROJECT.md)
- ADR/decision record this relates to

---

**Status:** Complete
**Version:** 1.0
**Migrated from:** docs/ia/custom/PROJECT/reality/something.md
**Migration date:** 2026-04-20
```

### Step 5: Update All Project References (5 min)

**Update each project that was using the custom version:**

```bash
# In docs/ia/custom/PROJECT_A/reality/current-system-state.md:
# BEFORE:
# See: docs/ia/custom/PROJECT_A/reality/concurrent-limits.md

# AFTER:
# See: /EXECUTION/spec/CANONICAL/decisions/ADR-007-concurrent-entity-constraints.md
# Project specialization: docs/ia/custom/PROJECT_A/SPECIALIZATIONS/constitution-*.md
```

**Also update:**

- Thread documentation (if it references old location)
- README files that link to the doc
- CHANGELOG in each project (optional)

**Checklist:**

```bash
# Search all project folders for references
grep -r "docs/ia/custom/PROJECT/reality/something.md" docs/ia/custom/

# Update each reference to point to new CANONICAL location
# Commit with message: "docs: Update references to ADR-007 migration"
```

### Step 6: Maintain Backwards Compatibility (3 min)

**Create redirect in old location:**

```bash
# Option 1: Replace with redirect doc
cat > docs/ia/custom/PROJECT/reality/concurrent-limits.md << 'EOF'
# ⬅️ MOVED — See Updated Location

This document has been promoted to CANONICAL.

**New location:**
[ADR-007: Implementation Guardrails (Design First)](../../decisions/ADR-007-implementation-guardrails-design-first.md)

**Reason:** Rule proven stable across multiple projects

**Migration date:** 2026-04-20
**Status:** Deprecated (use link above)

---
EOF

# Option 2: Remove entirely if no internal links
rm docs/ia/custom/PROJECT/reality/concurrent-limits.md
```

**Why maintain backwards compatibility?**

```
If you DELETE without redirect:
  ❌ Old Git history broken
  ❌ External links (in code comments) break
  ❌ Archives/backups reference wrong location

If you create redirect:
  ✅ Git history preserved
  ✅ External links still work (with message)
  ✅ Archives/backups automatically redirect
  ✅ Easy to find new location
```

### Step 7: Commit and Validate (5 min)

**Create atomic git commit:**

```bash
# Stage all changes
git add /EXECUTION/spec/CANONICAL/decisions/ADR-007-*.md
git add docs/ia/custom/*/reality/*.md          # Updated references
git add docs/ia/custom/*/reality/concurrent-limits.md  # Redirect

# Commit with clear message
git commit -m "docs: Migrate concurrent-limits to CANONICAL (ADR-007)

MIGRATION DETAILS:
- From: _spec/custom/_TEMPLATE/reality/concurrent-limits.md
- To: /EXECUTION/spec/CANONICAL/decisions/ADR-007-concurrent-entity-constraints.md
- Reason: Proven stable across [PROJECT_NAME] + [PROJECT_NAME]

CHANGES:
- Created ADR-007 with generalized rule
- Updated references in all projects
- Added redirect in original location for backwards compatibility

VALIDATION:
- All projects reference new CANONICAL location
- No broken links
- Old location still discoverable for 6 months
"

# Validate SPEC compliance
python docs/ia/SCRIPTS/validate-ia-first.py --audit docs/ia/

# Validate projects still work
python docs/ia/SCRIPTS/generate-specializations.py --project [PROJECT_NAME] --force
python docs/ia/SCRIPTS/generate-specializations.py --project [PROJECT_NAME] --force
```

---

## 🔄 Reverse Migration (custom/ ← CANONICAL)

**When to do this:** CANONICAL rule too specific, move to project-specific SPECIALIZATIONS

**Process (simplified):**

```
1. Identify rule in CANONICAL that's project-specific
2. Create custom/PROJECT/SPECIALIZATIONS/constitution-project-specific.md
3. Add project-specific version of rule
4. Update CANONICAL to reference the specialization
5. Mark original CANONICAL rule as deprecated (if fully replaced)
6. Commit with clear message
```

**Example:**

```
Move: "[PROJECT_NAME] max 50 concurrent campaigns"
From: /EXECUTION/spec/CANONICAL/specifications/performance.md
To: _spec/custom/_TEMPLATE/SPECIALIZATIONS/constitution-rpg-specific.md

In CANONICAL, update to:
"Projects define concurrent entity limits in their SPECIALIZATIONS"
"See: docs/ia/custom/[PROJECT]/SPECIALIZATIONS/constitution-*.md"
```

---

## 🚨 What NOT to Do

❌ **Mistake 1:** Move doc without generalizing it
- Result: CANONICAL has project-specific rules (breaks isolation)
- Fix: Remove project references first

❌ **Mistake 2:** Delete old location without redirect
- Result: Broken links in history, comments, external refs
- Fix: Keep redirect for 6+ months

❌ **Mistake 3:** Update references but not all projects
- Result: Some projects still reference old location
- Fix: Search all custom/ folders before committing

❌ **Mistake 4:** Forget to run validation after migration
- Result: SPEC compliance broken, CI/CD fails
- Fix: Run validate-ia-first + generate-specializations before commit

❌ **Mistake 5:** Migrate without team approval
- Result: Teams confused, breaking changes in their flow
- Fix: Get sign-off from architecture team + project leads

---

## 📋 Pre-Migration Checklist

Before migrating a doc:

- [ ] Doc has been in custom/ for at least 2 weeks (stable)
- [ ] Doc works in 2+ projects (proven)
- [ ] All project-specific content removed/generalized
- [ ] Correct CANONICAL layer identified (rules/decisions/specs)
- [ ] CANONICAL version created
- [ ] All project references updated
- [ ] Redirect created in original location
- [ ] Validation passed (validate-ia-first + generate-specializations)
- [ ] Architecture team reviewed + approved
- [ ] Project leads notified of change

---

## 📊 Migration Impact Template

**Use for team communication:**

```markdown
## Migration: [Doc Title]

**From:** docs/ia/custom/PROJECT/reality/document.md
**To:** /EXECUTION/spec/CANONICAL/decisions/ADR-007-*.md

**What changed for your project:**
- Reference: Update from old path to ADR-007
- Behavior: No change to rule itself (generalized version)
- Impact: Shared with other projects (better alignment)

**New project-specific guidance:**
- See: docs/ia/custom/PROJECT/SPECIALIZATIONS/constitution-*.md
- Projects can specialize the rule further if needed

**Action required:** None (automatic redirect in place)

**Timeline:** Old location will be removed 2026-05-19 (30 days notice)
```

---

## 🔗 Related Docs

- [architecture.md](../../canonical/specifications/architecture.md)
- [ADR-003: Ports & Adapters Pattern](../../decisions/ADR-003-ports-adapters-pattern.md)
- [ADDING_NEW_PROJECT.md](./ADDING_NEW_PROJECT.md)
- [ADDING_NEW_PROJECT.md](ADDING_NEW_PROJECT.md)

---

**Last Updated:** 2026-04-19
**Status:** Complete (v1.0)
**Use Case:** Proven with [PROJECT_NAME] + [PROJECT_NAME] pattern
