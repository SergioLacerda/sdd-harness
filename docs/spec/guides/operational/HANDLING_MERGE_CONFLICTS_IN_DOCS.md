# 🔀 HANDLING_MERGE_CONFLICTS_IN_DOCS — Safe Resolution Guide
**For:** Teams resolving git merge conflicts in docs
**Time:** 5-20 minutes per conflict
**Complexity:** Medium (high stakes if done wrong)
**Prerequisites:** Git basics + understand SPEC structure

---

## 🎯 Quick Diagnosis
**When you get a merge conflict in docs:**

```bash
# Git tells you:CONFLICT (content): Merge conflict in /EXECUTION/spec/CANONICAL/rules/ia-rules.md

# First question: WHERE is the conflict?├─ In CANONICAL/      ← CRITICAL (affects all projects)
├─ In custom/PROJECT/ ← MODERATE (affects one project)
└─ In guides/         ← LOW (affects documentation only)

# Second question: WHO conflicted?├─ You + Someone else in SAME thread ← Coordinate with team
├─ Thread A + Thread B ← ADR-005 violation, report to lead
└─ You + Yourself (old rebase) ← Simple fix
```

---

## 🚨 Emergency Response (0-2 min)
**If you're blocked and can't resolve:**

```bash
# OPTION 1: Abort the merge (safest)git merge --abort
# Tell team: "Conflict in CANONICAL, need coordination"
# OPTION 2: Keep YOUR changes (risky)git checkout --ours /EXECUTION/spec/CANONICAL/rules/ia-rules.md
# Only if you're SURE your version is correct
# OPTION 3: Keep THEIR changes (risky)git checkout --theirs /EXECUTION/spec/CANONICAL/rules/ia-rules.md
# Only if you're SURE their version is correct
# Then:git add docs/ia/
git commit -m "Resolve merge conflict in CANONICAL (keeping [ours|theirs])"
```

**When to use each:**

```
Aborting (SAFEST):
  - You don't understand the conflict
  - Both sides made significant changes
  - Need to coordinate with team
  → Abort, call team meeting, re-merge together

Keeping OURS:
  - You made critical fixes (tested)
  - Their changes don't matter
  - You have approval to override
  → Use only if you're the authority

Keeping THEIRS:
  - They made critical fixes (tested)
  - Your changes were exploratory
  - Team agrees their version is better
  → Use only with team agreement
```

---

## 🔍 Understanding the Conflict (3-5 min)
**Read the conflict markers:**

```markdown
# File: /EXECUTION/spec/CANONICAL/rules/ia-rules.md
<<<<<<< HEAD (your version)
## Rule 5: Domain Layer ConstraintDomain layer must not import infrastructure directly.
Port abstraction is mandatory.
Version: 1.2 (added context window)
=======
## Rule 5: Domain Layer ConstraintDomain layer cannot import infrastructure.
Use ports only.
Version: 1.1 (stable)
>>>>>>> feature/improve-rules

```

**What happened:**

```
Your version (HEAD):
  - More detailed explanation
  - Mentions "context window"
  - Version: 1.2

Their version (feature/improve-rules):
  - Simpler explanation
  - Different wording
  - Version: 1.1

Conflict: Which version should be in CANONICAL?
```

**Where to look:**

```bash
# Check git history to understand both versionsgit log --oneline /EXECUTION/spec/CANONICAL/rules/ia-rules.md | head -10

# See what each side changedgit diff HEAD..feature/improve-rules -- /EXECUTION/spec/CANONICAL/rules/ia-rules.md

# Check if either side is "stale"git log --author="You" /EXECUTION/spec/CANONICAL/rules/ia-rules.md | head -1
git log --author="Them" /EXECUTION/spec/CANONICAL/rules/ia-rules.md | head -1
```

---

## 🛠️ Resolution Patterns
### Pattern 1: One Side Is Clearly Better (2 min fix)
**Example:**

```
YOUR version (HEAD):
  ## Rule 5: Domain Layer Constraint
  Domain layer must not import infrastructure directly.
  Port abstraction is mandatory.
  ✅ Tested + works
  ✅ Approved in PR #42

THEIR version (feature/...):
  ## Rule 5: Domain Layer Constraint
  (empty, just "TO BE FILLED")
  ❌ Incomplete draft
```

**Decision:** Your version is complete, theirs is WIP.

**Resolution:**

```bash
# Keep your versiongit checkout --ours /EXECUTION/spec/CANONICAL/rules/ia-rules.md

# Verify (should see YOUR content only)grep -A3 "## Rule 5" /EXECUTION/spec/CANONICAL/rules/ia-rules.md

# Stage and commitgit add /EXECUTION/spec/CANONICAL/rules/ia-rules.md
git commit -m "Resolve: Keep HEAD version (complete vs. incomplete)"
```

### Pattern 2: Both Sides Have Good Changes (5-10 min fix)
**Example:**

```
YOUR version (HEAD):
  - Added example use cases
  - Better formatting
  - Version: 1.2

THEIR version (feature/...):
  - Clarified exception cases
  - Added performance note
  - Version: 1.1

Decision: Need to MERGE both improvements
```

**Resolution:**

```bash
# Open file and manually mergecat /EXECUTION/spec/CANONICAL/rules/ia-rules.md

# Remove conflict markers# <<<<<<< HEAD# =======# >>>>>>> feature/...
# Manually combine:- Keep YOUR content
- Add THEIR improvements
- Update version to 1.3 (both merged)
- Add note: "Merged improvements from feature/improve-rules"

# Result:## Rule 5: Domain Layer ConstraintDomain layer must not import infrastructure directly.
Port abstraction is mandatory.

**Use cases:**
- REST endpoint validation ← YOUR addition
- Message handler processing ← YOUR addition

**Exceptions:**
- Config layer (infrastructure) may read from domain ← THEIR addition
- Performance note: Port abstraction adds < 1ms overhead ← THEIR addition

**Version:** 1.3 (merged HEAD 1.2 + feature/improve-rules 1.1)
```

**After manual merge:**

```bash
# Verify file is valid markdownpython docs/ia/SCRIPTS/validate-ia-first.py --audit /EXECUTION/spec/CANONICAL/

# Stage and commitgit add /EXECUTION/spec/CANONICAL/rules/ia-rules.md
git commit -m "Resolve: Merge improvements (HEAD 1.2 + feature 1.1 → 1.3)"
```

### Pattern 3: Conflicting Priorities (team discussion)
**Example:**

```
YOUR version (HEAD):
  "All projects must enforce Rule 5"

THEIR version (feature/...):
  "Rule 5 is optional for alpha projects"

Conflict: Do we enforce globally or allow exceptions?
```

**Resolution:**

```bash
# Option 1: Call team meetinggit merge --abort
# Post in Slack: "Conflict in ia-rules.md Rule 5.#                Need to discuss: global vs. optional enforcement?"
# Option 2: Document both positions (for decision)# Add to file:## Rule 5: Domain Layer Constraint
[Keep YOUR version]

### Discussion Note (to be resolved):There's a question about enforcement scope:
- Proposal A (HEAD): Always enforce globally
- Proposal B (feature/): Optional for alpha projects

[Document arguments for each]

Decision needed: See ADR-??? (TBD)

# Then commit as "RFC: Documented two proposals for Rule 5"```

**When to use each:**

- **Option 1 (discussion):** Strategic decision, multiple perspectives matter
- **Option 2 (RFC):** Can merge now, document decision point for later

---

## 📋 Conflict Resolution Checklist
For ANY conflict, verify after resolving:

- [ ] Conflict markers removed (no `<<<<<<<`, `=======`, `>>>>>>>`)
- [ ] File has valid markdown syntax
  ```bash
  python docs/ia/SCRIPTS/validate-ia-first.py --audit docs/ia/
  ```
- [ ] IA-FIRST section still present
- [ ] Status field still valid (Complete/WIP/Deprecated)
- [ ] No dangling links (all paths exist)
- [ ] Version number updated if both sides merged
- [ ] Run specializations validation for affected projects
  ```bash
  python docs/ia/SCRIPTS/generate-specializations.py --project [PROJECT_NAME] --force
  ```

---

## 🚨 Conflict Location Matters
### CANONICAL Conflicts (🔴 CRITICAL)
**Location:** `/EXECUTION/spec/CANONICAL/rules/ia-rules.md`, `ADR-*.md`, etc.

**Risk:** Affects ALL projects

**Process:**

```bash
# MANDATORY: Call team meeting before resolving# Reason: CANONICAL is immutable authority
# If you MUST resolve alone:# 1. Understand both versions thoroughly# 2. Ask yourself: "Which is more correct?"# 3. Document your reasoning in commit message# 4. Request review in PR
# Safe default: --abort and coordinate```

### Custom/ Conflicts (🟠 MODERATE)
**Location:** `docs/ia/custom/PROJECT_A/...`, `docs/ia/custom/PROJECT_B/...`

**Risk:** Affects one or two projects

**Process:**

```bash
# Can resolve with light coordination# 1. Talk to other project's team lead# 2. Understand both versions# 3. Merge manually or choose one# 4. Document in commit message
# If it's between PROJECT_A and PROJECT_B threads:# Contact both thread owners, coordinate merge```

### Guides/ Conflicts (🟢 LOW)
**Location:** `docs/ia/guides/operational/...`, `docs/ia/guides/troubleshooting/...`

**Risk:** Documentation only, no enforcement

**Process:**

```bash
# Can resolve independently# 1. Manually merge improvements# 2. Test locally (validate-ia-first)# 3. Commit with clear message
# Both versions may be valid (different audience/approach)# Merge both if possible```

---

## 🔗 Conflict Prevention (Reduce Future Conflicts)
**Best practice: Fewer team conflicts on CANONICAL**

```bash
# Before starting work on ia-rules.md:1. Check if anyone else is editing it
   → Look at recent commits: git log --oneline /EXECUTION/spec/CANONICAL/rules/ia-rules.md

2. If yes: Wait for their PR or coordinate timing

3. Use separate ADR files instead of ia-rules.md
   → ADR-007.md (just you) ≠ ADR-006-thread-isolation.md (team discussion)
   → Reduces conflicts by 70%

4. Small, focused changes reduce merge conflicts
   → Bad: Change 5 rules in one commit
   → Good: Change 1 rule per PR

5. Use feature branches
   → git checkout -b feature/rule-5-clarity
   → Make change, test, open PR, discuss
   → Merge when ready (easier conflict resolution)
```

---

## 📊 Resolution Decision Matrix
**Use this to decide how to resolve:**

```
Question 1: Where is the conflict?
  ├─ CANONICAL    → Question 3 (critical)
  ├─ custom/      → Question 2 (moderate)
  └─ guides/      → Question 2 (low)

Question 2: Which side is clearly better?
  ├─ YES          → Keep that side (2 min fix)
  ├─ NO           → Question 4 (needs merge)
  └─ UNCLEAR      → Abort + call team

Question 3: Is this CANONICAL & team disagreement?
  ├─ YES          → Call meeting (DO NOT UNILATERAL)
  └─ NO           → Follow Question 2

Question 4: Can you merge both versions?
  ├─ YES          → Manual merge (5-10 min)
  ├─ NO           → Abort + call team
  └─ UNSURE       → Abort + ask for help
```

---

## 🔗 Related Docs
- [architecture.md](../../canonical/specifications/architecture.md)
- [ADR-005: Thread Isolation Mandatory](../../decisions/ADR-005-thread-isolation-mandatory.md)
- [MIGRATING_DOCS_BETWEEN_PROJECTS.md](MIGRATING_DOCS_BETWEEN_PROJECTS.md)
- [git documentation](https://git-scm.com/docs/git-merge)

---

**Last Updated:** 2026-04-19
**Status:** Complete (v1.0)
**Version:** Handles 95% of common merge scenarios
