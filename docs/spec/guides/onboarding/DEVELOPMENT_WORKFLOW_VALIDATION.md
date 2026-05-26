# 💓 DEVELOPMENT WORKFLOW VALIDATION — The Heart of Our Operation

**For:** AI Agents, Developers, Team Leads
**Purpose:** Validate that developers follow CORRECT workflow (read → context → implement → validate → test)
**Success Metric:** 95%+ developer confidence in workflow, zero rule violations, first-time PR approval 90%+

---

## 🎯 THE WORKFLOW (5 Phases)

```
┌──────────────────────────────────────────────────┐
│ DEVELOPMENT WORKFLOW (The Heart)                 │
├──────────────────────────────────────────────────┤
│                                                  │
│  PHASE 1: READ DOCS (5 min)                     │
│  └─ constitution.md + ia-rules.md + quiz        │
│                                                  │
│  PHASE 2: PREPARE CONTEXT (10-15 min)           │
│  └─ Load docs by PATH (A/B/C/D)                 │
│  └─ Check execution-state                        │
│                                                  │
│  PHASE 3: IMPLEMENT (1-4 hours)                 │
│  └─ Follow feature-checklist.md                 │
│  └─ Test as you go                              │
│  └─ Use ports correctly                         │
│                                                  │
│  PHASE 4: VALIDATE (5-10 min)                   │
│  └─ Run tests locally                           │
│  └─ Check definition_of_done.md                 │
│                                                  │
│  PHASE 5: TEST & CHECKPOINT (10 min)            │
│  └─ Final pytest run                            │
│  └─ Update execution-state/_current.md          │
│  └─ Create PR with context                      │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## ✅ WORKFLOW VALIDATION CHECKLIST

Use this to verify CONFIDENCE in the workflow:

### PHASE 1: READ DOCS ✅

**Expected Actions:**

```
Developer opens:
  1. /EXECUTION/spec/CANONICAL/rules/constitution.md
     └─ Reads: 15 immutable principles
     └─ Time: 3 minutes
     └─ Understands: "These rules never change"

  2. /EXECUTION/spec/CANONICAL/rules/ia-rules.md
     └─ Reads: 16 execution protocols
     └─ Time: 2 minutes
     └─ Understands: "These are mandatory"

  3. Takes VALIDATION_QUIZ.md
     └─ Score: ≥80%
     └─ Understands: Validated the 5 core concepts
```

**Validation Questions (ask developer):**

```
Q1: "What's the source of truth when documents conflict?"
A:  "constitution.md is immutable and takes precedence"
    ✅ If correct → Understanding validated

Q2: "Can you modify code in Thread B if it helps Thread A?"
A:  "No, thread isolation is mandatory"
    ✅ If correct → Understanding validated

Q3: "What must you do after implementing a feature?"
A:  "Update execution-state/_current.md with decisions, risks, and status"
    ✅ If correct → Understanding validated

Q4: "Can you import infrastructure directly?"
A:  "No, always use ports"
    ✅ If correct → Understanding validated

Q5: "What if documentation is wrong?"
A:  "Document the gap with evidence, update docs, timestamp it"
    ✅ If correct → Understanding validated
```

**Red Flags:**

```
❌ Developer skips constitution.md (says "just rules")
❌ Developer skips ia-rules.md (says "just documentation")
❌ Developer fails quiz (< 80%)
❌ Developer takes quiz but doesn't understand why answers are correct
❌ Developer says "I'll just ask for help if I break something"
```

**Remediation:**

```
If ANY red flag:
  1. Have developer re-read that section (with time limit)
  2. Re-take quiz
  3. Continue only when 100% confident
  4. Don't rush this phase
```

---

### PHASE 2: PREPARE CONTEXT ✅

**Expected Actions:**

```
Developer:
  1. Reads: /EXECUTION/spec/CANONICAL/rules/conventions.md
     └─ Time: 3 minutes
     └─ Knows: Naming, file structure, patterns

  2. Reads: /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md
     └─ Time: 3 minutes
     └─ Knows: Active threads, conflicts, blockers
     └─ Verifies: No conflicts with planned work

  3. Based on PATH (A/B/C/D):
     └─ Loads ONLY relevant docs (not all 85KB)
     └─ Time: 10-15 min depending on PATH
     └─ Has mental model: architecture, ports, tests
```

**Validation Questions:**

```
Q1: "What's your PATH?"
A:  "A (bug fix)" or "B (simple feature)" etc.
    ✅ If clear → Chosen correctly

Q2: "Why did you choose that PATH?"
A:  "Because I'm fixing [specific thing in one layer]" or "Because I'm adding [new feature across 2 layers]"
    ✅ If reasoning is sound → Choice validated

Q3: "What docs did you load?"
A:  Lists 4-6 specific files for their PATH
    ✅ If matches PATH requirements → Context loaded correctly

Q4: "Any conflicts with execution-state?"
A:  "I checked. No conflicts" or "I saw Thread X, but it's unrelated"
    ✅ If verified → Execution-state checked

Q5: "What are 3 key constraints you'll hit?"
A:  Can name 3 constraints from docs (from limitations/ or architecture.md)
    ✅ If named correctly → Context understood
```

**Red Flags:**

```
❌ Developer loads ALL docs ("I'll read everything")
❌ Developer doesn't check execution-state
❌ Developer can't name their PATH
❌ Developer can't explain why they chose that PATH
❌ Developer hasn't read conventions.md yet
❌ Developer discovers known_issue AFTER implementing (should have been in Phase 2)
```

**Remediation:**

```
If ANY red flag:
  1. Have developer check execution-state NOW
  2. Have developer re-read conventions.md
  3. Have developer name 3 constraints from docs
  4. Continue when validated
```

---

### PHASE 3: IMPLEMENT ✅

**Expected Behavior:**

```
Developer:
  1. Opens feature-checklist.md for their PATH
     └─ Reads: Checklist items (domain/port/usecase/etc)
     └─ Follows: EXACTLY in order

  2. For EACH checklist item:
     └─ Implements the piece
     └─ Writes tests IMMEDIATELY (not at the end)
     └─ Validates that piece works
     └─ Moves to next item

  3. When stuck:
     └─ Consults: testing.md, conventions.md, architecture.md
     └─ Does NOT ask team first (reads docs first)
     └─ If docs don't answer: Ask team with context (what you tried, where stuck)

  4. Uses PORTS correctly:
     └─ Never imports infrastructure directly
     └─ Always uses port interface
     └─ Can explain why (ports = abstraction)
```

**Validation Questions (ongoing):**

```
Q1: "Show me feature-checklist.md. Are you following it?"
A:  Developer can point to specific checklist items + show code for each
    ✅ If following checklist → Implementation structured

Q2: "Where are your tests?"
A:  Developer has tests for EVERY checklist item (not all at the end)
    ✅ If tests exist → TDD pattern followed

Q3: "Did you use a port or import infrastructure directly?"
A:  Developer shows: "I used [PortName] from contracts.md"
    ✅ If ports used → Architecture followed

Q4: "What did you do when stuck?"
A:  "I searched docs/ia/ for 'keyword', found [file.md], that answered it"
    ✅ If docs-first → Workflow followed

Q5: "Any violations of ia-rules.md?"
A:  Developer proactively checks (doesn't wait for code review)
    ✅ If checking themselves → Self-aware
```

**Red Flags:**

```
❌ Developer writes all code, then all tests (anti-pattern)
❌ Developer imports infrastructure directly (violates ports rule)
❌ Developer skips feature-checklist.md
❌ Developer says "I'll just make it work and refactor later"
❌ Developer leaves TODO/FIXME comments (should be resolved now)
❌ Developer doesn't understand why they chose a pattern
❌ Developer implements feature outside their layer (crosses boundaries)
```

**Remediation:**

```
If ANY red flag DURING implementation:
  1. Stop and fix it NOW (don't wait for PR review)
  2. Check feature-checklist.md again
  3. Write missing tests
  4. Validate ports are used
  5. Continue only when validated
```

---

### PHASE 4: VALIDATE ✅

**Expected Behavior:**

```
Developer:
  1. Runs: pytest tests/ -k "my_feature" (or pytest)
     └─ ALL PASS
     └─ If fail: FIX NOW (don't commit failing tests)

  2. Checks: definition_of_done.md
     └─ All boxes checked ✅
     └─ If unchecked: FIX NOW

  3. Verifies: No ia-rules.md violations
     └─ No direct infrastructure imports
     └─ No cross-thread modifications
     └─ Ports used correctly
     └─ If violations: FIX NOW
```

**Validation Questions:**

```
Q1: "Do all tests pass?"
A:  "Yes, pytest shows 100% pass"
    ✅ If pass → Ready for next phase

Q2: "Have you checked definition_of_done.md?"
A:  Developer shows checklist with all boxes ✅
    ✅ If all checked → Quality gate met

Q3: "Did you re-read ia-rules.md violations?"
A:  Developer can explain: "I checked for [violation X], found none"
    ✅ If self-validated → Understanding reinforced
```

**Red Flags:**

```
❌ Tests fail but developer says "I'll fix later"
❌ definition_of_done.md has unchecked boxes
❌ Developer hasn't verified ports usage
❌ Developer says "Tests are probably fine, let's see in CI"
```

**Remediation:**

```
If ANY red flag:
  1. Developer must fix NOW
  2. Re-run pytest until ALL PASS
  3. Re-check definition_of_done.md
  4. Continue only when validated
```

---

### PHASE 5: TEST & CHECKPOINT ✅

**Expected Behavior:**

```
Developer:
  1. Final pytest run:
     pytest tests/ --cov=src/rpg_narrative_server
     └─ All tests pass ✅
     └─ Coverage meets threshold ✅

  2. Update execution-state/_current.md:
     - What I implemented
     - Decisions made
     - Open questions
     - Risks identified
     - Status: COMPLETE
     └─ Timestamp + name

  3. Create PR with:
     - Clear title (includes PATH: [PATH-X])
     - Description (what/why/how/testing/risks)
     - Link to checkpoint in execution-state
     - Request specific reviewer (if needed)
```

**Validation Questions:**

```
Q1: "Does pytest show 100% pass + coverage met?"
A:  Yes, shows report
    ✅ If yes → Ready for PR

Q2: "Did you update execution-state/_current.md?"
A:  Yes, shows entry with timestamp + details
    ✅ If yes → Checkpoint created

Q3: "Can you explain your PR description?"
A:  Developer explains in one sentence (what), one sentence (why), lists files
    ✅ If clear → PR ready

Q4: "Any risks or open questions?"
A:  Developer lists them (if none, says "None identified")
    ✅ If transparent → Reviewers informed
```

**Red Flags:**

```
❌ Tests don't pass but PR is created anyway
❌ execution-state/_current.md not updated
❌ PR description is vague or copy-paste
❌ Developer doesn't mention risks ("Nothing could go wrong")
❌ Coverage is below threshold
```

**Remediation:**

```
If ANY red flag:
  1. Block PR creation (don't push yet)
  2. Fix tests/checkpoint/description
  3. Re-validate
  4. Then create PR
```

---

## 📊 WORKFLOW CONFIDENCE METRICS

Use these to measure if developers are confident in workflow:

### Metric 1: Time Per Phase

**Expected Times (PATH B - Simple Feature):**

```
Phase 1 (Read docs):        5 min  (goal: 3-5 min)
Phase 2 (Prepare context): 15 min  (goal: 10-15 min)
Phase 3 (Implement):      100 min  (goal: 90-120 min)
Phase 4 (Validate):        10 min  (goal: 5-10 min)
Phase 5 (Checkpoint):      10 min  (goal: 10 min)

TOTAL: ~140 minutes (2.5 hours) ✅

If developer takes 4+ hours → confidence issue (too much re-reading/second-guessing)
If developer takes 45 min → quality issue (skipped phases)
```

**How to Measure:**

```
Ask developer: "From start to PR creation, how much time?"
- < 45 min → Skipping phases (investigate)
- 45-180 min → Expected (good)
- > 3 hours → Over-analysis (coach on phase efficiency)
```

### Metric 2: First-Time PR Approval Rate

**Target:** 90%+ of PRs approved on first review (no requested changes)

**Current State:** Unknown (needs measurement)

**Causes of PR Rejection:**

```
❌ ia-rules.md violations (architecture issues)
   └─ Indicates: Phase 1 not understood

❌ Tests missing (quality issues)
   └─ Indicates: Phase 3 not followed correctly

❌ execution-state not updated
   └─ Indicates: Phase 5 skipped

❌ Code style issues
   └─ Indicates: conventions.md not read

❌ Missing ports usage
   └─ Indicates: architecture.md not understood
```

**Improvement Path:**

```
PR rejection → Identify which phase failed → Re-train on that phase → 2nd PR should pass
```

### Metric 3: Self-Validation Before PR

**Target:** 100% of developers check BEFORE committing

**Validation Signs:**

```
✅ Developer runs: pytest tests/ (before PR)
✅ Developer checks: definition_of_done.md (before PR)
✅ Developer verifies: No ia-rules violations (before PR)
✅ Developer updated: execution-state (before PR)

If ANY missing → developer might skip later too → coach on Phase 4
```

### Metric 4: Question Pattern

**Target:** Developers ask questions AFTER checking docs

**Good Pattern:**

```
Developer: "I looked at architecture.md section X, but it doesn't explain Y. Where should I find this?"
→ Shows: Docs-first thinking, specific question
→ Answer: Specific file or "You discovered a gap!"

Bad Pattern:**
```

Developer: "How do I do X?"
→ Shows: No docs check, lazy thinking
→ Answer: "Check [file.md] first, then come back"

```

---

## 🎯 TEAM VALIDATION PROTOCOL

Every 2 weeks, validate TEAM workflow confidence:

### Week 1-2 Audit

```

1. Pick 2-3 recent PRs
2. Trace each PR back through the 5 phases:
   - Did they read constitution.md + ia-rules.md? (check their checkpoint)
   - Did they load context by PATH? (check checkpoint + file sizes)
   - Did they follow feature-checklist? (check code structure)
   - Did they validate? (check tests + definition_of_done)
   - Did they update checkpoint? (check execution-state history)

3. For each gap found:
   - Identify which phase failed
   - Note pattern (is this developer struggling?)
   - Decide: Re-train or improve docs for that phase?

4. Report findings:
   - X% of PRs follow complete workflow
   - Phase Y is most commonly skipped
   - Recommendation: [action]

```

---

## 🆘 WHEN WORKFLOW CONFIDENCE BREAKS

**Scenario 1: Developer Keeps Violating ia-rules.md**

```

Symptom: PR rejected 3x for direct infrastructure imports
Root cause: Developer didn't understand ports concept in Phase 1
Fix:

  1. Have developer re-read: ADR-003-ports-adapters-pattern.md
  2. Ask: "Why are ports needed?" (get correct answer)
  3. Next PR: Have reviewer specifically check port usage
  4. Follow up: Was fix successful?

```

**Scenario 2: Developer Skips Tests**

```

Symptom: PR has code but no tests
Root cause: Developer thought tests were "polish" (Phase 3 not followed)
Fix:

  1. Have developer read: testing.md (your layer)
  2. Ask: "Why write tests as you go?" (get correct answer)
  3. Next PR: Require tests BEFORE committing
  4. Follow up: Did developer implement tests?

```

**Scenario 3: Developer Doesn't Update Checkpoint**

```

Symptom: PR merged but execution-state/_current.md still old
Root cause: Developer didn't understand checkpointing (Phase 5 not followed)
Fix:

  1. Have developer re-read: ia-rules.md "Checkpointing Protocol"
  2. Ask: "Why update checkpoint?" (get correct answer)
  3. Next PR: Block merge until checkpoint updated
  4. Follow up: Did developer remember?

```

**Scenario 4: Developer Takes 5+ Hours Per PR**

```

Symptom: Developer seems productive but very slow
Root cause: Over-analysis in Phases 2 or 4
Fix:

  1. Ask: "Which phase takes longest?"
  2. If Phase 2: "You're loading too much context. Use ONLY your PATH."
  3. If Phase 4: "You're second-guessing yourself. Tests pass? Done."
  4. Set time limits: Phase 2 = 15 min max, Phase 4 = 10 min max

```

---

## ✅ FINAL VALIDATION CHECKLIST (Team Lead)

Use this monthly to validate TEAM workflow confidence:

```

PHASE 1 (Read Docs) - CONFIDENCE: __/10
  ✅ All new devs take VALIDATION_QUIZ
  ✅ 80%+ pass rate on first try
  ✅ No PRs rejected for ia-rules violations
  ✅ When violations happen, dev understands "why I violated it"

PHASE 2 (Prepare Context) - CONFIDENCE: __/10
  ✅ Developers can name their PATH
  ✅ Context size matches PATH (no 200KB loads for bug fix)
  ✅ Developers check execution-state before starting
  ✅ No surprised blockers ("I didn't know Thread X existed")

PHASE 3 (Implement) - CONFIDENCE: __/10
  ✅ Developers write tests DURING implementation
  ✅ Developers use ports correctly (not direct imports)
  ✅ Developers follow feature-checklist.md structure
  ✅ Code follows conventions.md patterns

PHASE 4 (Validate) - CONFIDENCE: __/10
  ✅ All tests pass locally before PR
  ✅ definition_of_done.md fully checked before PR
  ✅ Developers self-validate ia-rules before submitting
  ✅ No tests fail in CI (means they run locally)

PHASE 5 (Test & Checkpoint) - CONFIDENCE: __/10
  ✅ execution-state updated in 100% of PRs
  ✅ PR descriptions are clear and complete
  ✅ 90%+ PRs approved on first review
  ✅ Risks/questions documented proactively

OVERALL CONFIDENCE: ___/50 (or __/10 averaged)

```

---

## 🎓 INTERPRETATION GUIDE

```

50/50 points (10/10):
  → Perfect workflow adherence
  → Team is highly confident
  → Rare PR rejections
  → Predictable, high-quality output

40-49/50 points (8-9.8/10):
  → Good workflow adherence
  → Team is confident
  → 85%+ PR approval on first review
  → Minor gaps (e.g., Phase 2 sometimes skipped)

30-39/50 points (6-7.8/10):
  → Partial workflow adherence
  → Team is somewhat confident
  → 70%+ PR approval
  → Gaps in specific phases

< 30/50 points (< 6/10):
  → Workflow not established
  → Team lacks confidence
  → High PR rejection rate
  → Need to restart training

```

---

## 🎯 SUCCESS CRITERIA (FINAL)

**Developer workflow confidence is HIGH when:**

✅ Developers can explain why each phase exists
✅ Developers follow phases automatically (no reminding needed)
✅ Developers catch their own mistakes (before code review)
✅ Developers rarely violate ia-rules.md
✅ 90%+ of PRs approved on first review
✅ New developers productive in < 1 day
✅ Questions are specific ("How do I test X?" vs "How do I test?")
✅ Checkpoints updated consistently
✅ Zero "I didn't know that existed" surprises

---

**Version:** 1.0
**Created:** April 19, 2026
**Authority:** AGENT_HARNESS.md + CANONICAL/rules/ia-rules.md
**Owner:** Team Lead / Architecture Team
**Frequency:** Validate monthly, adjust quarterly
