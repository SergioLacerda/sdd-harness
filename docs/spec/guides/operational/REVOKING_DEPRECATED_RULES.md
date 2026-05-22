# 🗑️ REVOKING_DEPRECATED_RULES — Lifecycle Guide

**For:** Architecture teams deprecating old governance rules
**Time:** 30-60 minutes per rule revocation
**Complexity:** High (impacts all projects)
**Prerequisites:** Understand SPEC layers + multi-project impact

---

## 🎯 When to Revoke a Rule

**Revoke when:**

```
Question 1: Is this rule still needed?
  NO → Continue to Q2
  YES → Don't revoke (yet)

Question 2: Have all projects adapted?
  YES → Continue to Q3
  NO → Create migration plan first

Question 3: Is there a replacement rule?
  YES → Document migration path
  NO → Still mark deprecated (but with warning)

Result: Ready to revoke
```

**Examples:**

```
✅ SHOULD REVOKE:
   "Developers must manually validate all PRs"
   → Replaced by: "CI/CD gate validates automatically"
   → All projects adapted: YES
   → Time: Safe to revoke now

✅ SHOULD REVOKE:
   "Store all data in JSON files"
   → Replaced by: "Store in PostgreSQL (migration path available)"
   → All projects adapted: 2/3 projects
   → Time: NOT YET (wait for 3/3)

❌ SHOULD NOT REVOKE:
   "Thread isolation mandatory"
   → Replacement: None (still core)
   → Status: Mark as permanent (never revoke)
```

---

## 🔄 3-Phase Revocation Process

### Phase 1: Planning (5-10 min)

**Create revocation ticket:**

```markdown
# Revocation Ticket: Rule X Name

**Rule:** [Name of rule being revoked]
**Location:** /EXECUTION/spec/CANONICAL/rules/ia-rules.md
**Current version:** 1.5
**Reason for revocation:** [Brief explanation]

**Replacement:** [If exists]
  - New rule/process: [link]
  - Migration steps: [link to migration guide]

**Impact assessment:**
- Projects affected: [list]
- Breaking changes: [yes/no/describe]
- Migration effort: [estimate in hours]

**Timeline:**
- Deprecation announcement: [date]
- Migration deadline: [date + 30 days]
- Final revocation: [date + 60 days]
- Grace period: [30 days after final]

**Approval:**
- [ ] Architecture team: [Names]
- [ ] Project leads: [Names]
```

**Share with team:** Post in Slack + get sign-off

### Phase 2: Deprecation (Visible Warning - 2 weeks)

**Step 1: Update rule in CANONICAL**

**Location:** `/EXECUTION/spec/CANONICAL/rules/ia-rules.md`

**Change status from "Active" to "Deprecated":**

```markdown
## Rule 5: Old Process ⚠️ DEPRECATED

**Status:** Deprecated (end of life: 2026-05-19)

**What changed:**
This rule is being phased out in favor of automated validation.

**Why deprecated:**
Manual validation became unnecessary after CI/CD gates implemented.
See: [ADR-008: Automated Validation Gates](../decisions/ADR-008-automated-validation-gates.md)

**Timeline:**
- **Deprecation notice:** 2026-04-19 (today)
- **Migration deadline:** 2026-05-19 (30 days) — MUST switch to new process
- **Final removal:** 2026-06-19 (60 days)
- **Grace period:** Until 2026-07-19 (90 days) — old references still work but warn

**Migration path:**
1. Read: [Migration guide: Manual to Automated Validation](../guides/MIGRATING_MANUAL_TO_AUTOMATED_VALIDATION.md)
2. Update your process: [Steps here]
3. Test with old + new process running in parallel (1 week)
4. Switch to new process on 2026-05-19
5. Report completion to: #architecture-team

**FAQ:**
Q: Can I keep using the old rule?
A: Only until 2026-05-19. After that, CI/CD gates will enforce new process.

Q: What if I'm in the middle of a feature?
A: Finish feature with old rule, then migrate (grace period exists).

Q: Who do I contact if stuck?
A: Post in #architecture-team channel

---

[Rest of rule details...]

**Related:**
- Replaced by: [New process/rule]
- Deprecation ticket: #456
- Migration guide: [link]
```

**Step 2: Create migration guide**

**Location:** `docs/ia/guides/operational/MIGRATING_RULE5_DEPRECATION.md`

```markdown
# Migration Guide: Rule 5 Deprecation

**From:** Manual validation (OLD, deprecated)
**To:** Automated CI/CD validation (NEW, required)

**Timeline:** Must complete by 2026-05-19

---

## Migration Checklist

- [ ] Read deprecation notice (Rule 5 in ia-rules.md)
- [ ] Understand new process (Step 1 below)
- [ ] Test new process in isolated branch (Step 2)
- [ ] Run both processes in parallel (1 week)
- [ ] Switch to new process (Step 3)
- [ ] Remove old validation from workflow
- [ ] Commit migration + notify team
- [ ] Archive old process (Step 4)

---

## Step 1: Understand New Process

[Detailed explanation of new automated validation]

## Step 2: Test in Isolated Branch

[Testing procedures]

## Step 3: Production Migration

[Steps to switch over]

## Step 4: Archive Old Process

[How to clean up old documentation/scripts]

---

**Questions?** Post in #architecture-team
```

**Step 3: Communicate to team**

```markdown
📢 ANNOUNCEMENT: Rule 5 Deprecation Notice

**Rule:** Manual validation process
**Status:** DEPRECATED as of 2026-04-19
**Action deadline:** 2026-05-19 (30 days)

**What this means:**
You must switch from manual validation to automated CI/CD validation.
After 2026-05-19, manual validation will no longer be supported.

**Steps:**
1. Read: ia-rules.md, Rule 5 (deprecation notice)
2. Follow: guides/operational/MIGRATING_RULE5_DEPRECATION.md
3. Test: New process in a branch
4. Migrate: Switch before 2026-05-19

**Timeline:**
- 2026-04-19: Deprecation announced (today)
- 2026-05-19: Migration deadline (30 days)
- 2026-06-19: Old rule removed (60 days)
- 2026-07-19: Grace period ends (90 days)

**Help:**
- Question? → Post in #architecture-team
- Blocked? → Reply to this thread

**Questions?** I'm here to help. Don't wait until the deadline!
```

**Share:** Slack, all-hands, project kick-off

---

### Phase 3: Final Removal (After deadline)

**Step 1: Verify all projects migrated**

```bash
# Search for old rule references
grep -r "old-rule-name\|manual-validation" docs/ia/custom/

# If found:
# - Contact project owner
# - If they don't respond: Force update (coordinated)

# Verify no code still uses old process
grep -r "old_validation_function" src/

# If found: File issue with team
```

**Step 2: Update rule to "Removed"**

**Location:** `/EXECUTION/spec/CANONICAL/rules/ia-rules.md`

```markdown
## Rule 5: Manual Validation ❌ REMOVED

**Status:** Removed (2026-06-19)

**Replacement:** See [Automated Validation Process](../specifications/ci-cd-gates.md)

**Why removed:**
Replaced by CI/CD automated gates (more reliable, faster feedback).

**Migration:**
All projects successfully migrated by 2026-05-19.
See: [Migration guide](../guides/MIGRATING_RULE5_DEPRECATION.md) (archived)

**Grace period:** Until 2026-07-19 (30 days after removal)
**Final cleanup:** 2026-07-19 (remove redirect references)

---

[OLD RULE CONTENT REMOVED — See Git history for details]
```

**Step 3: Mark migration guide as archived**

**Update:** `docs/ia/guides/operational/MIGRATING_RULE5_DEPRECATION.md` header

```markdown
# ⬅️ ARCHIVED: Migration Guide — Rule 5 Deprecation

**Status:** Archived (migration completed 2026-06-19)

**Purpose:** Historical record of deprecation process

---

[Keep for historical reference]
```

**Step 4: Create deprecation summary in ADR**

```markdown
# ADR-008: Deprecation of Manual Validation Rule

**Date:** 2026-06-19
**Status:** Accepted

**Context:**
Manual validation rule (Rule 5 in ia-rules.md) no longer needed after
automated CI/CD gates implemented.

**Decision:**
Deprecated Rule 5 (2026-04-19) → Removed (2026-06-19)

**Timeline:**
- Deprecation: 2026-04-19
- Migration deadline: 2026-05-19
- Removal: 2026-06-19
- Final cleanup: 2026-07-19

**Consequences:**
- All projects must use automated validation
- Manual validation no longer supported
- CI/CD gates now enforce validation automatically

**Related:**
- Old rule: Rule 5 in ia-rules.md (removed)
- Migration guide: docs/ia/guides/operational/MIGRATING_RULE5_DEPRECATION.md (archived)
- New process: [Automated Validation Gates spec]
```

---

## 🔄 Multi-Project Coordination

**Critical: All projects must agree**

```bash
# BEFORE revoking, verify:
✅ PROJECT_A adapted: YES/NO?
✅ PROJECT_B adapted: YES/NO?
✅ All future projects will use new process: YES/NO?

# If any NO:
# → Create migration plan for that project
# → Don't revoke until all adapted
```

**Coordination process:**

```
1. Send notice to all project leads
   "Rule X will be deprecated 2026-04-19"
   "Migration deadline: 2026-05-19"

2. Track migration status in shared sheet
   | Project | Status | Completion | Owner |
   |---------|--------|------------|-------|
   | A       | ✅     | 2026-04-22 | [Name] |
   | B       | 🔄     | TBD        | [Name] |
   | C       | ⏱️     | 2026-05-10 | [Name] |

3. Weekly check-in: "Who needs help?"

4. By 2026-05-19: All must be complete
   If not: Extend deadline + escalate

5. Final removal: Only after 100% completion
```

---

## 🚨 If a Project Misses Deadline

**What to do:**

```bash
# If PROJECT_B not migrated by 2026-05-19:

# Option 1: Extend deadline (if legitimate blocker)
"PROJECT_B needs 2 more weeks, extending to 2026-06-02"
→ But: No later than this

# Option 2: Force migration (if procrastinating)
# Architecture team:
# 1. Assigns someone to migrate PROJECT_B
# 2. Coordinates with PROJECT_B team
# 3. Tests migration in PR
# 4. Merges with their approval
# → They must test afterward

# Option 3: Escalate (if refusing to migrate)
# If PROJECT_B refuses:
# 1. Document refusal + reasons
# 2. Escalate to VP Engineering
# 3. Make strategic decision (keep rule? sunset project?)
```

---

## 📊 Revocation Success Metrics

**Before finalizing revocation, verify:**

| Metric | Target | Status |
|--------|--------|--------|
| All projects migrated | 100% | ✅/❌ |
| No code references old rule | 0% | ✅/❌ |
| Zero support requests after 7 days | ✅ | ✅/❌ |
| New projects use new process | 100% | ✅/❌ |
| CI/CD validation working | 100% pass rate | ✅/❌ |

---

## 🛑 What NOT to Do

❌ **Mistake 1:** Revoke without deprecation period
- Result: Projects break suddenly
- Fix: Always 30-day deprecation notice

❌ **Mistake 2:** Revoke without migration guide
- Result: Confusion, incorrect migrations
- Fix: Create step-by-step migration docs

❌ **Mistake 3:** Revoke without all projects adapted
- Result: Some projects still use old rule (breaks enforcement)
- Fix: Don't revoke until 100% migrated

❌ **Mistake 4:** Delete old rule content entirely
- Result: Can't understand why rule existed
- Fix: Keep in git history (archive in docs)

❌ **Mistake 5:** Revoke unilaterally (without team)
- Result: Projects surprised, angry
- Fix: Announce 30 days early, get sign-off

---

## 📋 Revocation Checklist

Before removing rule permanently:

- [ ] Deprecation notice published (30 days ago minimum)
- [ ] Migration guide created + shared
- [ ] All project leads confirmed migration complete
- [ ] Code search shows no references to old rule
- [ ] Support tickets resolved (no questions)
- [ ] New project template uses new process
- [ ] CI/CD validates new process is working
- [ ] Grace period notice announced (30 days before final cleanup)
- [ ] Final removal documented in ADR
- [ ] Old content archived (git history preserved)
- [ ] Team notified of completion

---

## 🔗 Related Docs

- [architecture.md](../../CANONICAL/specifications/architecture.md)
- [ia-rules.md](../../CANONICAL/rules/ia-rules.md)
- [ADR-005: Thread Isolation Mandatory](../../CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md)
- [MIGRATING_DOCS_BETWEEN_PROJECTS.md](MIGRATING_DOCS_BETWEEN_PROJECTS.md)

---

**Last Updated:** 2026-04-19
**Status:** Complete (v1.0)
**Tested pattern:** For future deprecations
