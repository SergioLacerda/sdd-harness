# 🎯 AGENT HARNESS — Confident Development Workflow

**For:** AI Agents, Developers, Teams
**Purpose:** Start ANY work with confidence using proven practices
**Time to First PR:** 30-40 minutes
**Success Rate:** 100% if following this guide

---

## 🚀 THE AGENT HARNESS (30-40 minutes)

**This is THE entry point for all work.** Follow this sequence exactly.

### PHASE 1: LOCK TO RULES (5 minutes) — MANDATORY

#### Step 1.1: Read Constitution & Rules
```
READ NOW (in this order):
  1. /EXECUTION/spec/CANONICAL/rules/constitution.md (3 min)
     └─ 15 immutable principles that NEVER change
     └─ If confused later: These are source of truth

  2. /EXECUTION/spec/CANONICAL/rules/ia-rules.md (2 min)
     └─ 16 MANDATORY execution protocols
     └─ Violating these = system failures
```

**Why this first?**
> "You can implement brilliant code that violates these rules and breaks the entire system."

#### Step 1.2: Take Validation Quiz (5 min)
```
RUN IMMEDIATELY:

Option A (Humans/Manual):
  1. Open: docs/spec/guides/onboarding/VALIDATION_QUIZ.md
  2. Answer 5 questions
  3. Score yourself (must be ≥80%)
  4. If < 80%: Re-read ia-rules.md + retry

Option B (AI Agents):
  1. Verify you understand these 5 concepts:
     A. Source of truth: constitution.md > ia-rules.md > everything else
     B. Thread isolation: Never modify other threads
     C. Checkpointing: Update execution-state/_current.md after changes
     D. Ports: Never import infrastructure directly, always use ports
     E. Gap documentation: Real ≠ Docs is normal, document it + evidence

  2. If unclear on ANY: Re-read that section of ia-rules.md
  3. Continue only when 100% confident
```

**If you fail or skip this step:** You will violate rules unknowingly → PR rejected → waste time.

---

### PHASE 2: UNDERSTAND PROJECT STATE (3 minutes)

#### Step 2.1: Check Execution State

```
READ IMMEDIATELY:
  /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md

Answers these questions:
  - Is there active work I should know about?
  - Are there conflicts with my planned work?
  - What threads exist? Am I assigned to one?
  - What's the current blocker/risk?
```

**If you see CONFLICTS:**
```
❌ DO NOT PROCEED
✅ ASK the team via Slack with:
   - What you want to do
   - Why execution-state says conflict
   - Request: permission to proceed or alternative task
```

**If clear:**
```
✅ Continue to Phase 3
```

---

### PHASE 3: CHOOSE YOUR PATH (1 minute)

#### Step 3.1: Match Task to PATH

```
DECISION TREE (60 seconds):

Is this a...?

┌─ Bug fix or small change?
│  └─ YES → PATH A (1-1.5h, ~40KB context)
│           Focus: One layer, one component, one test suite
│           Example: "Fix cache invalidation in MemoryService"
│
├─ New feature touching 1-2 layers?
│  └─ YES → PATH B (2h, ~45KB context)
│           Focus: New domain concept + port + use case
│           Example: "Add session timeout feature (domain+app layer)"
│
├─ Complex feature touching 3+ layers?
│  └─ YES → PATH C (3-4h, ~85KB context)
│           Focus: Multiple entities, multiple services, orchestration
│           Example: "Thread-safe concurrent campaigns"
│
└─ Parallel work (isolated from others)?
   └─ YES → PATH D (variable time, isolated context)
           Focus: Your thread only, no cross-thread modifications
           Example: "Implement RAG optimization (separate thread)"
```

**Your PATH:** _____ (record this)

---

### PHASE 4: LOAD CONTEXT (10-15 minutes depending on PATH)

#### Step 4.1: Universal Context (always load)

```
✅ LOAD NOW (5 min):
   1. /EXECUTION/spec/CANONICAL/rules/conventions.md
      └─ Code naming, file structure, patterns

   2. /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/_INDEX.md
      └─ Master index of what exists
      └─ Which services? Which data models? Which contracts?
```

#### Step 4.2: Path-Specific Context

**IF PATH A (Bug Fix):**
```
✅ LOAD (5 min):
   1. /EXECUTION/spec/CANONICAL/specifications/architecture.md
      └─ Section: Your affected layer only

   2. /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/known_issues.md
      └─ Bug might already be there!
      └─ Or known workarounds

   3. /EXECUTION/spec/CANONICAL/specifications/testing.md
      └─ How to test the layer you're fixing

   4. /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/services.md
      └─ The service you're modifying
```

**IF PATH B (Simple Feature):**
```
✅ LOAD (10 min):
   1. /EXECUTION/spec/CANONICAL/specifications/architecture.md (full)
   2. /EXECUTION/spec/CANONICAL/specifications/feature-checklist.md (layers 1-3 only)
   3. /EXECUTION/spec/CANONICAL/specifications/testing.md (your layers)
   4. /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/contracts.md
      └─ Ports you'll use/implement
   5. /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/data_models.md
      └─ DTOs, request/response contracts
```

**IF PATH C (Complex Feature):**
```
✅ LOAD (15 min):
   1. /EXECUTION/spec/CANONICAL/specifications/architecture.md (full)
   2. /EXECUTION/spec/CANONICAL/decisions/ADR-*.md (relevant ADRs only)
   3. /EXECUTION/spec/CANONICAL/specifications/feature-checklist.md (full)
   4. /EXECUTION/spec/CANONICAL/specifications/testing.md (full)
   5. /EXECUTION/spec/custom/_TEMPLATE/reality/current-system-state/ (all files)
   6. /EXECUTION/spec/custom/_TEMPLATE/reality/limitations/ (all files)
      └─ Known constraints you'll hit
```

**IF PATH D (Multi-Thread):**
```
✅ LOAD (10 min):
   1. /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/threads/[YOUR_THREAD].md
      └─ What's already decided in your thread?
      └─ What are next steps?

   2. /EXECUTION/spec/CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md
      └─ Thread rules

   3. /EXECUTION/spec/custom/_TEMPLATE/reality/limitations/threading_concurrency.md
      └─ Concurrency constraints
```

---

### PHASE 5: IMPLEMENT WITH CONFIDENCE (1-4 hours depending on PATH)

#### Step 5.1: Follow Feature Checklist

```
USE: /EXECUTION/spec/CANONICAL/specifications/feature-checklist.md

Your PATH has a specific checklist:
  PATH A: Domain layer? → Application layer? → Tests? ✅
  PATH B: Ports? → Domain? → Use case? → Tests? ✅
  PATH C: Full 8-layer checklist ✅
  PATH D: Thread isolation checklist ✅

Follow EXACTLY. Skip = failures.
```

#### Step 5.2: Write Tests As You Go

```
From /EXECUTION/spec/CANONICAL/specifications/testing.md:

  PATH A: Layer tests (unit) + integration
  PATH B: Port contract tests + use case tests
  PATH C: Full pyramid (unit → integration → golden)
  PATH D: Thread isolation tests + concurrency tests

Tests FIRST (or as you go), not at the end.
```

#### Step 5.3: Ask When Uncertain

```
If you hit ANY confusion:

  Q: "Where does this go in the architecture?"
  A: Read architecture.md section for your layer

  Q: "How should I test this?"
  A: Read testing.md for your layer

  Q: "What port should I use?"
  A: Check contracts.md for existing ports

  Q: "What's the naming convention?"
  A: Check conventions.md

  Q: "Is this a known issue?"
  A: Check known_issues.md

  Q: "Can I use X library?"
  A: Check SPECIALIZATIONS_CONFIG.md (allowed dependencies)

  BLOCKED COMPLETELY?
  → Slack team with context (what you're doing, where stuck)
```

---

### PHASE 6: VALIDATION & CHECKPOINT (5-10 minutes)

#### Step 6.1: Test Locally

```
✅ RUN:
   pytest tests/ -k "your_feature"

✅ ALL PASS?
   Continue to 6.2

✅ ANY FAIL?
   Fix before committing
```

#### Step 6.2: Update Checkpoint

```
✅ EDIT: /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md

Add (or update if already exists):
  - What you implemented
  - Decisions you made
  - Open questions (if any)
  - Risks identified
  - Thread status (if multi-thread)
  - Your name + timestamp

Example:
  [2026-04-19 @ agent-1] Implemented session timeout feature
  - Decision: 30-min timeout (from _current.md requirements)
  - Question: Should timeout be per-campaign or global? (TBD in PR review)
  - Risk: May invalidate active sessions on deploy (document in runbook)
  - Status: Complete, ready for PR
```

#### Step 6.3: Definition of Done

```
Before creating PR, verify:

  ✅ Code follows conventions.md
  ✅ Tests pass locally (pytest)
  ✅ Tests follow testing.md patterns
  ✅ Ports used correctly (no direct infrastructure access)
  ✅ Thread isolation maintained (if multi-thread)
  ✅ No WIP/TODO comments left in code
  ✅ execution-state/_current.md updated
  ✅ No bypassed rules (re-read ia-rules.md if unsure)

All ✅? Continue to PR.
```

---

### PHASE 7: CREATE PR (5 minutes)

#### Step 7.1: PR Title & Description

```
TITLE:
  [PATH-A] Fix cache invalidation in MemoryService
  [PATH-B] Add session timeout feature
  [PATH-C] Implement concurrent campaign execution
  [PATH-D] (Thread name) Optimize RAG pipeline

DESCRIPTION:
  What: 1 sentence
  Why: Link to execution-state/_current.md or ADR
  How: List affected layers/files
  Testing: What tests verify this works?
  Risks: Any gotchas for reviewers?
```

#### Step 7.2: Link to Checkpoint

```
Add to PR description:
  "Checkpoint: /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md"

Reviewers can then see:
  - What you decided
  - What's still open
  - What risks exist
```

---

## ✅ VALIDATION CHECKLIST (Before You Start)

Before proceeding past Phase 1, verify:

```
✅ Read constitution.md (3 min)
✅ Read ia-rules.md (2 min)
✅ Passed validation quiz (≥80%)
✅ Understand: constitution.md is source of truth
✅ Understand: Thread isolation is mandatory
✅ Understand: Ports must be used, never bypass
✅ Understand: Checkpointing is mandatory
✅ Understand: Gap documentation is normal
```

**If ANY unchecked:** Re-read that section. Don't skip.

---

## 🚨 COMMON MISTAKES TO AVOID

### ❌ Mistake #1: Skipping the Quiz
**Why it's bad:** You won't understand the core rules → violations later → PR rejected
**Solution:** Take it seriously, it's only 5 minutes

### ❌ Mistake #2: Skipping execution-state/_current.md check
**Why it's bad:** You might modify someone else's thread → conflict → wasted work
**Solution:** ALWAYS read current.md before Phase 2

### ❌ Mistake #3: Loading too much context
**Why it's bad:** Token waste, slower decision making
**Solution:** Load ONLY what your PATH needs

### ❌ Mistake #4: Not updating checkpoint after work
**Why it's bad:** Next agent doesn't know what you did → duplicates work or contradicts you
**Solution:** Checkpoint is as important as code

### ❌ Mistake #5: Asking questions instead of consulting docs
**Why it's bad:** Blocks team, you learn slower
**Solution:** grep -r "keyword" docs/ia/ first, then ask

### ❌ Mistake #6: Skipping tests while implementing
**Why it's bad:** Late discovery of failures, quality issues
**Solution:** Test as you go, not at the end

### ❌ Mistake #7: Not following feature-checklist.md
**Why it's bad:** Missed layers, incomplete implementation
**Solution:** Checklist is your quality gate

---

## 📊 TIME BREAKDOWN

| Phase | Time | Why |
|-------|------|-----|
| 1. Lock to Rules | 5 min | Non-negotiable foundation |
| 2. Check State | 3 min | Prevent conflicts |
| 3. Choose PATH | 1 min | Context optimization |
| 4. Load Context | 10-15 min | Task-specific guidance |
| 5. Implement | 1-4 hours | Depends on PATH |
| 6. Validate | 5-10 min | Quality gate |
| 7. PR + Checkpoint | 5 min | Documentation |
| **TOTAL** | **30-50 min** | **First PR ready** |

---

## 🔗 YOUR NEXT ACTIONS (RIGHT NOW)

```
1. Open: /EXECUTION/spec/CANONICAL/rules/constitution.md (start Phase 1)
2. Set timer: 5 minutes
3. Read section 1-3 only (skim is OK)
4. Then: Open ia-rules.md (2 min read)
5. Then: Take VALIDATION_QUIZ.md
6. Then: Come back to Phase 2
```

---

## 🆘 IF STUCK

```
Can't find something?
  → grep -r "keyword" docs/ia/

Quiz failing?
  → Re-read that ia-rules.md section (10 min)
  → Don't skip this, it's your foundation

Execution state has conflicts?
  → Post in Slack: "I want to [task], execution-state says [conflict], permission?"

Implementation stuck?
  → 1. Check feature-checklist.md for your layer
  → 2. Check testing.md for your layer
  → 3. Check code + tests (best documentation)
  → 4. Ask team (include context from steps 1-3)

PR review feedback?
  → 1. Check if it's an ia-rules.md violation
  → 2. Check if it's a conventions.md issue
  → 3. Check if reviewer is right (trust the system)
  → 4. Fix + re-push

Don't know PATH?
  → Go to Phase 3 decision tree
  → If still unclear: Slack team (one message, we clarify in reply)
```

---

## 📈 SUCCESS LOOKS LIKE

After following AGENT_HARNESS:

✅ You understand the 5 core rules (constitution + ia-rules)
✅ You know what work is already in progress (execution-state)
✅ You know exactly which docs to read (by PATH)
✅ You implement with tests (not after)
✅ You update checkpoint (others know what you did)
✅ You create a clean PR (reviewers have context)
✅ No PR rejections for "violated ia-rules"
✅ First-time PR approval rate: 90%+

---

## 🎓 MASTERY PROGRESSION

| Stage | Knowledge | Time to Next |
|-------|-----------|--------------|
| Novice | Know PATH A | 1 day |
| Intermediate | Know PATHs A+B | 1 week |
| Advanced | Know PATHs A-D | 2 weeks |
| Expert | Can teach others, can design new PATHs | 1 month |

This guide is your foundation for ALL stages.

---

## 📝 SIGNATURE

**Version:** 1.0
**Created:** April 19, 2026
**Authority:** CANONICAL/rules/ia-rules.md
**Next Review:** When new team member completes AGENT_HARNESS successfully

---

## 🔄 FEEDBACK LOOP

After completing AGENT_HARNESS + first PR:

1. **Actual time taken:** Was it 30-40 min or different?
2. **Which phase was hardest?** 1, 2, 3, 4, 5, 6, or 7?
3. **Did you need help?** Where?
4. **Would different PATH description help?**

Post in Slack → Help us improve the next developer's experience.
