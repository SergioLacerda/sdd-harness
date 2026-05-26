# 📋 ONBOARDING CONSOLIDATION — Unified Entry Point

**Status:** Implementation guide for consolidating 3 onboarding paths into 1 clear entry
**Date:** April 19, 2026
**Objective:** Remove confusion, establish AGENT_HARNESS as canonical entry point

---

## 🎯 BEFORE (Current Confusion)

```
Three competing onboarding paths exist:

1. FIRST_SESSION_SETUP.md
   └─ 20-minute orientation
   └─ Includes VALIDATION_QUIZ
   └─ Comprehensive but slow

2. ULTRA_QUICK_ONBOARDING.md
   └─ 3-minute path
   └─ Setup wizard automation
   └─ No quiz, no clarity on which docs

3. QUICK_START.md
   └─ 3-minute PATH selection
   └─ Adaptive context loading
   └─ Technical, assumes some knowledge

→ NEW DEVELOPER sees 3 guides and asks: "Which one?"
→ Result: Confusion, skipped steps, rule violations
```

---

## ✅ AFTER (New Structure)

```
ONE canonical entry point with multiple modes:

AGENT_HARNESS.md (Primary)
  └─ 7-phase workflow (30-40 min)
  └─ Mandatory QUIZ after Phase 1
  └─ Covers: Rules, context, implementation, validation, checkpoint

Entry Points (Different Triggers, Same Destination):
  ├─ Copilot Chat → Links to AGENT_HARNESS
  ├─ Terminal (setup-wizard.py) → Validates AGENT_HARNESS + guides through
  ├─ VSCode Settings → Includes AGENT_HARNESS reference
  ├─ Cursor IDE → Suggests AGENT_HARNESS
  └─ Pre-Commit → Enforces AGENT_HARNESS compliance

Supporting Guides (Supplementary):
  ├─ QUICK_START.md → "I know the rules, just tell me PATH + docs" (2 min)
  ├─ ENTRY_POINTS_BY_TOOL.md → "I want to use [tool], what's the entry?"
  ├─ DEVELOPMENT_WORKFLOW_VALIDATION.md → "Is my team following workflow?"
  └─ VALIDATION_QUIZ.md → "Test your understanding of ia-rules"

Deprecated (Keep for reference, but stop recommending):
  ├─ FIRST_SESSION_SETUP.md (archived/legacy)
  └─ ULTRA_QUICK_ONBOARDING.md (archived/legacy)
```

---

## 🔄 MIGRATION PLAN (For Team)

### Step 1: Update All Links (1 hour)

**In these files, replace OLD links with NEW:**

```
OLD: "Start with FIRST_SESSION_SETUP.md"
NEW: "Start with AGENT_HARNESS.md"

OLD: "Use ULTRA_QUICK_ONBOARDING.md for fast start"
NEW: "For fast start, run: python docs/ia/SCRIPTS/setup-wizard.py"
     (which enforces AGENT_HARNESS first)

OLD: "Use QUICK_START.md to choose PATH"
NEW: "AGENT_HARNESS Phase 3 will guide you through PATH selection"
     (QUICK_START is secondary for experienced devs)
```

**Files to Update:**

- [ ] .github/copilot-instructions.md
- [ ] docs/spec/_INDEX.md (master index)
- [ ] docs/spec/guides/onboarding/README.md (if exists)
- [ ] docs/spec/guides/navigation/INDEX.md
- [ ] README.md (root level)
- [ ] Any other links to old onboarding

### Step 2: Mark Old Guides as Deprecated (1 hour)

Add to top of FIRST_SESSION_SETUP.md:

```markdown
# ⚠️ DEPRECATED — Use AGENT_HARNESS Instead

**This guide is kept for reference only.**

**→ NEW developers should use:** [AGENT_HARNESS.md](AGENT_HARNESS.md)

Historical note: This was the original onboarding guide (20-min version).
It's been replaced by a more focused and practical workflow.

If you found this helpful and want the old guide: You can still read it below.
```

Add to top of ULTRA_QUICK_ONBOARDING.md:

```markdown
# ⚠️ ARCHIVED — Use setup-wizard.py Instead

**This guide is archived but available for reference.**

**→ For fast onboarding:** Run `python docs/ia/SCRIPTS/setup-wizard.py`

This setup wizard enforces AGENT_HARNESS requirements while providing fast automation.
```

### Step 3: Update .github/copilot-instructions.md (2 hours)

Replace entire file with:

```markdown
# 🎯 AI GOVERNANCE — Agent Initialization Protocol

**For:** GitHub Copilot, Claude, Cursor, all AI agents
**Purpose:** Bootstrap correct workflow from first interaction
**Version:** 2.0 (Consolidated)

---

## SESSION STARTUP (MANDATORY FOR EVERY SESSION)

When starting work in this project, you MUST:

1. **Direct user to AGENT_HARNESS first**

   ```

   User: "Help me fix the session timeout bug"

   Copilot Response:
     "Great! Before we start coding, please follow AGENT_HARNESS
     (30-40 min one-time setup) to ensure you have the right foundation.

     Read: docs/spec/guides/onboarding/AGENT_HARNESS.md

     Quick summary:
     - Phase 1 (5 min): Read constitution.md + ia-rules.md + take QUIZ
     - Phase 2 (3 min): Check execution-state for conflicts
     - Phase 3 (1 min): Choose your PATH (A/B/C/D)
     - Phase 4 (10-15 min): Load docs for your PATH
     - Phase 5-7: Implement + validate + update checkpoint

     Have you completed AGENT_HARNESS? (If yes → I'll help you code)"

   ```

2. **Verify VALIDATION_QUIZ completion**

   ```

   If user says NO to AGENT_HARNESS:
     "Please complete it first. It only takes 30-40 min and includes:
      - Understanding of 16 mandatory execution protocols
      - PATH selection quiz
      - Execution state verification

     Without this, we might violate project rules. Start here:
     docs/spec/guides/onboarding/AGENT_HARNESS.md (Phase 1)"

   If user says YES but you doubt their understanding:
     "Quick validation: What's the source of truth when docs conflict?"
     (Answer: "constitution.md is immutable")

     If wrong → "Let me explain. Read: /EXECUTION/spec/CANONICAL/rules/constitution.md"

   ```

3. **Use ENTRY_POINTS_BY_TOOL to guide tool-specific setup**

   ```

   Copilot user: "I'm confused about how to start"

   Response:
     "You're using GitHub Copilot. Here's your entry point:
      docs/spec/guides/onboarding/ENTRY_POINTS_BY_TOOL.md
      → Section: 'ENTRY POINT #1: GITHUB COPILOT'

     But first: Have you completed AGENT_HARNESS?"

   ```

---

## WORKFLOW ENFORCEMENT (During Session)

### Rule #1: Ports Mandatory (ADR-003)

```

If you suggest code that imports infrastructure directly:
  ❌ Remove it. Replace with port.

Example:
  ❌ from src.infrastructure.storage.json_adapter import JSONAdapter
  ✅ from src.domain.ports import StoragePort

```

### Rule #2: Tests Before/During Implementation

```

If user asks how to implement X:

✅ DO: "First, understand what tests you need for X.
        Read: /EXECUTION/spec/CANONICAL/specifications/testing.md
        Then let's write tests first, implement second."

❌ DON'T: "Here's the implementation code. Tests come later."

```

### Rule #3: Thread Isolation (ADR-005)

```

If user wants to modify code outside their thread:
  ❌ Block it.

"You're in Thread A. This code is in Thread B (or shared CANONICAL).
 Thread isolation is mandatory per ADR-005.
 /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/threads/

 What you CAN do:

 1. Modify only Thread A code
 2. Update CANONICAL/ only if universally applicable
 3. Document conflicts in execution-state/_current.md"

```

### Rule #4: Checkpointing Mandatory

```

After implementation, you MUST:
  "Update checkpoint: /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md

  Include:

- What you implemented
- Decisions made
- Open questions
- Risks
- Timestamp + your name"

```

### Rule #5: Conventions First

```

Before suggesting code:

  1. Check: /EXECUTION/spec/CANONICAL/rules/conventions.md (naming, structure)
  2. Follow patterns from existing code
  3. If uncertain: Ask user to check conventions.md first

```

---

## CONTEXT OPTIMIZATION

### When Suggesting Docs

✅ **DO suggest PATH-specific:**
```

"For a bug fix (PATH A), you need:

  1. conventions.md (naming)
  2. architecture.md (affected layer only)
  3. testing.md (layer tests)
  4. known_issues.md (maybe already documented!)
  5. services.md (affected service)

  Total: ~40KB, 5-15 min read"

```

❌ **DON'T suggest everything:**
```

"Here's all 85KB of docs..."

```

### When Loading Context

✅ **DO ask first:**
```

"What's your PATH?
  A. Bug fix (1-1.5h)
  B. Simple feature (2h)
  C. Complex feature (3-4h)
  D. Multi-thread work (variable)

I'll load ONLY the relevant docs for that PATH."

```

❌ **DON'T assume:**
```

"Let me load everything just in case..."

```

---

## ERROR HANDLING

### If User Violates ia-rules.md

```

Pattern: User's code violates a protocol (e.g., direct infrastructure import)

Response:

  1. Show the violation: "Line X: This imports infrastructure directly"
  2. Explain the rule: "Ports are mandatory per ADR-003"
  3. Provide fix: "Replace with [PortName] from contracts.md"
  4. Link to docs: "/EXECUTION/spec/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md"
  5. Prevent: "Going forward, always use ports"

```

### If User Is Confused

```

Pattern: User asks vague question like "How do I test this?"

Response:

  1. Clarify: "What component are you testing?"
  2. Guide: "Read testing.md for [component] patterns"
  3. Then: "Try writing a test following this pattern, show me"
  4. Support: "Need help understanding the pattern?"

```

### If User Blocked by Execution State Conflict

```

Pattern: execution-state/_current.md shows active thread conflict

Response:

  1. Identify conflict: "Thread B is currently active on [subsystem]"
  2. Prevent damage: "Don't modify Thread B code"
  3. Escalate: "Slack team: 'I want to work on X, but Thread B is active on Y'"
  4. Wait: "Team will clarify next steps"

```

---

## SPECIAL GUIDANCE BY ROLE

### For New Developers (First Day)

```

1. Complete AGENT_HARNESS (30-40 min)
2. Ask: "What's your first task?"
3. Guide them through PATH selection
4. Load ONLY their PATH docs
5. Pair program on first commit
6. Review their execution-state checkpoint

```

### For Experienced Developers (Jumping to Code)

```

1. Ask: "Have you taken the QUIZ in AGENT_HARNESS?"
2. If YES: "Great! What's your PATH?"
3. If NO: "Even for experienced devs, 5 min to pass QUIZ. Worth it."
4. Load PATH docs quickly
5. Implement with familiar patterns
6. Checkpoint + PR

```

### For Multi-Thread Work

```

1. Have them read: /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/threads/
2. Identify their thread: "You're in [Thread Name]"
3. Read thread requirements
4. Enforce isolation: "Only modify code in your thread"
5. Update thread checkpoint in execution-state

```

---

## COMPLIANCE CHECKS (Pre-PR)

Before user creates PR, validate:

```

✅ QUIZ passed (≥80%)
✅ execution-state checked (no conflicts)
✅ PATH selected (A/B/C/D)
✅ Docs loaded (correct docs for PATH)
✅ Tests written (during implementation, not after)
✅ Ports used (no direct imports)
✅ Checkpoint updated (decisions + risks documented)
✅ definition_of_done.md checked
✅ No ia-rules violations
✅ Code follows conventions.md

If ANY unchecked:
  "Can't create PR yet. Here's what's missing: [list]"

```

---

## FEEDBACK LOOP

After user's first PR:

```

1. PR approved?
   YES: "Congratulations! You followed AGENT_HARNESS correctly."
   NO: "Let's debug together. Which phase went wrong?"

2. Actual time taken?
   Record and update AGENT_HARNESS if estimate was off

3. Any confusion?
   Note and improve AGENT_HARNESS or docs

4. Ready for next task?
   "Great! Your PATH is [A/B/C/D]. Use same approach."

```

---

## SUMMARY

**This instruction file enforces:**
- ✅ AGENT_HARNESS completion (mandatory)
- ✅ VALIDATION_QUIZ passing (mandatory)
- ✅ No ia-rules violations (mandatory)
- ✅ Checkpointing (mandatory)
- ✅ Adaptive context by PATH (efficiency)
- ✅ Tests before PR (quality)
- ✅ Ports usage (architecture)

**Result:** Consistent, high-quality workflow with 90%+ first-PR approval rate.

---

**Version:** 2.0 Consolidated
**Updated:** April 19, 2026
**Authority:** AGENT_HARNESS.md + CANONICAL/rules/ia-rules.md
**Status:** Ready for Implementation
```

### Step 4: Update setup-wizard.py (1 hour)

**Modify to validate AGENT_HARNESS completion:**

```python
# docs/ia/SCRIPTS/setup-wizard.py (updated)

def main():
    print_header()

    # NEW: Require AGENT_HARNESS completion first
    print("\n" + Colors.BOLD + Colors.BLUE + "Step 0: AGENT_HARNESS Verification" + Colors.END)
    print("\nBefore using this wizard, you MUST complete AGENT_HARNESS.")
    print("Link: docs/spec/guides/onboarding/AGENT_HARNESS.md")

    response = ask_question(
        "Have you completed AGENT_HARNESS (read constitution + ia-rules + passed quiz)?",
        ["Yes, I completed it", "No, show me where to go"]
    )

    if response == "No, show me where to go":
        print(f"\n{Colors.RED}Please complete AGENT_HARNESS first:{Colors.END}")
        print("  1. Open: docs/spec/guides/onboarding/AGENT_HARNESS.md")
        print("  2. Follow Phases 1-2 (about 8 minutes)")
        print("  3. Take the VALIDATION_QUIZ (5 minutes)")
        print("  4. Come back and run this wizard again")
        exit(0)

    # Continue with existing wizard...
    path = determine_path()
    # ... rest of wizard
```

### Step 5: Announce Deprecation (Email + Slack)

**Send to team:**

```
Subject: Onboarding Consolidated → AGENT_HARNESS is now primary

Hi team!

We've consolidated onboarding into ONE clear pathway: AGENT_HARNESS

📍 NEW STRUCTURE:
  Primary: docs/spec/guides/onboarding/AGENT_HARNESS.md (7 phases, 30-40 min)
  Entry Points: Copilot, VSCode, Cursor, Terminal, Pre-Commit, CI/CD
  Supporting: QUICK_START.md (for quick PATH reminder), VALIDATION_QUIZ.md, WORKFLOW_VALIDATION.md

🔄 DEPRECATED (but kept for reference):
  - FIRST_SESSION_SETUP.md (archived)
  - ULTRA_QUICK_ONBOARDING.md (use setup-wizard.py instead)

✅ IF YOU'RE NEW:
  Start here: docs/spec/guides/onboarding/AGENT_HARNESS.md (30-40 min)

✅ IF YOU'RE EXPERIENCED:
  Have you taken the VALIDATION_QUIZ? If yes: You're ready.
  If no: 5 min quiz ensures you know the rules.

❓ Questions?
  Post in #architecture channel

Timeline:
  - Today: All links updated
  - This week: All PRs must follow AGENT_HARNESS
  - Next week: Old guides moved to ARCHIVE

Questions? Ask me!
```

---

## 📋 CONSOLIDATION CHECKLIST

- [ ] Create AGENT_HARNESS.md ✅
- [ ] Create ENTRY_POINTS_BY_TOOL.md ✅
- [ ] Create DEVELOPMENT_WORKFLOW_VALIDATION.md ✅
- [ ] Mark FIRST_SESSION_SETUP.md as deprecated (add warning header)
- [ ] Mark ULTRA_QUICK_ONBOARDING.md as archived (add warning header)
- [ ] Update .github/copilot-instructions.md (use template above)
- [ ] Update setup-wizard.py (enforce AGENT_HARNESS first)
- [ ] Update docs/spec/_INDEX.md (link AGENT_HARNESS as primary)
- [ ] Update docs/spec/guides/onboarding/README.md (if exists)
- [ ] Send team announcement (email + Slack)
- [ ] Move old guides to docs/spec/ARCHIVE/deprecated-onboarding/ (optional)
- [ ] Create docs/spec/ARCHIVE/ONBOARDING_MIGRATION_LOG.md (what changed when)

---

## ✅ SUCCESS METRICS

After consolidation:

- ✅ New developer asks "Where do I start?" → Answer: "AGENT_HARNESS"
- ✅ 100% of PRs reference AGENT_HARNESS in their checkpoint
- ✅ 90%+ first-time PR approval rate
- ✅ Zero "Which guide?" confusion
- ✅ Quiz pass rate ≥80% for all new devs
- ✅ All onboarding entry points (Copilot/Cursor/terminal) link to AGENT_HARNESS

---

**Version:** 1.0
**Created:** April 19, 2026
**Status:** Ready for Implementation
