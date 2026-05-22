# 📋 VALIDATION QUIZ — Understanding ia-rules.md

**When**: Right after reading `ia-rules.md` in FIRST_SESSION_SETUP.md
**Duration**: 5 minutes
**Goal**: Verify you understand the 16 protocols before proceeding
**Passing Score**: 80% (4/5 correct)

---

## 🎯 Why This Quiz?

`ia-rules.md` contains 16 NON-NEGOTIABLE execution protocols. Skipping these = failures.

This quiz forces the rules into your working memory **before** you start working.

---

## 📝 QUIZ QUESTIONS

### Question 1: The Hierarchy

**What is the source of truth priority when documents conflict?**

A) `ia-rules.md` — because it has the most rules
B) `constitution.md` — because it's most stable
C) `execution_state.md` — because it's most recent
D) Whichever file you trust most

**Correct Answer**: B ✅
**Reasoning**: `constitution.md` is immutable and takes precedence over everything. Rules stop execution conflicts.

**If wrong**: Re-read [ia-rules.md](../../ia-rules.md) section "Source of Truth Priority"

---

### Question 2: Thread Isolation

**You're working on a bug in Thread A. Can you modify code in Thread B if it helps fix Thread A?**

A) Yes, good engineering is being flexible
B) No, thread isolation is mandatory
C) Only if you update execution_state.md
D) Only if Thread B is inactive

**Correct Answer**: B ✅
**Reasoning**: Thread isolation is MANDATORY (ADR-005). Each thread works in isolation to prevent conflicts. No cross-thread modifications.

**If wrong**: Re-read [ADR-005-thread-isolation-mandatory.md](../../decisions/ADR-005-thread-isolation-mandatory.md)

---

### Question 3: Checkpointing

**After implementing a feature, what MUST you do?**

A) Just commit the code, documentation updates are optional
B) Update `/docs/ia/DEVELOPMENT/execution-state/_current.md` with:
   - Decisions taken
   - Open questions
   - Risks identified
   - Thread status
C) Run the test suite
D) Notify the team via Slack

**Correct Answer**: B ✅
**Reasoning**: Checkpointing is mandatory (ia-rules protocol #14). Executable + documentation state in sync prevents the system diverging from its spec.

**If wrong**: Re-read [ia-rules.md](../../ia-rules.md) section "Checkpointing Protocol"

---

### Question 4: Ports

**Your code needs to read from storage. Can you import `storage/adapters/json_adapter.py` directly?**

A) Yes, it's already implemented
B) No, always go through the Storage Port interface
C) Only if the adapter is "public"
D) Only if you document why

**Correct Answer**: B ✅
**Reasoning**: Bypassing ports (ia-rules protocol #1) creates fragility. Ports are abstraction layers. Always use ports, never infrastructure directly.

**If wrong**: Re-read [ADR-003-ports-adapters-pattern.md](../../decisions/ADR-003-ports-adapters-pattern.md)

---

### Question 5: Assumption vs Reality

**You notice `known_issues.md` says "Vector index can be slow" but you think it's wrong based on your observation. What do you do?**

A) Update `known_issues.md` immediately
B) Ignore it and implement your solution
C) Document your finding + evidence in execution_state.md
   Then update known_issues.md with timestamp
D) Trust the documentation, don't question it

**Correct Answer**: C ✅
**Reasoning**: ia-rules protocol #16 "Gap documentation": Reality ≠ docs is normal. Document gaps, include evidence, update tracking. Don't assume docs are wrong.

**If wrong**: Re-read [ia-rules.md](../../ia-rules.md) section "When Reality Differs from Specs"

---

## ✅ How to Validate Yourself

**For Claude agents** (automatic):
```
Score tracking is logged to:
  → /docs/ia/REALITY/current-system-state/_quiz_tracking.json

Your score appears in:
  → execution_state.md (under "Agent Readiness" section)
```

**For humans** (manual):
```
Count correct answers: ___/5

If ≥ 4 correct (80%):
  ✅ PASS — Proceed to work

If < 4 correct (< 80%):
  ❌ RETRY — Re-read ia-rules.md, try again in 30 min
```

---

## 🔄 Next Steps

**If you PASSED (4+ correct)**:
1. Continue with FIRST_SESSION_SETUP.md (minute 9+)
2. Read `/docs/ia/guides/QUICK_START.md` to choose your PATH
3. Proceed to work ✓

**If you FAILED (< 4 correct)**:
1. ❌ Stop here
2. 📖 Re-read `/EXECUTION/spec/CANONICAL/rules/ia-rules.md` (full, 10 min)
3. Wait 30 minutes (memory consolidation)
4. Retake this quiz
5. After passing: continue with setup

---

## 📊 Scoring & Tracking

**This quiz measures**:
- Understanding of core protocols ✓
- Ability to follow mandatory rules ✓
- Risk awareness (ports, isolation, etc.) ✓

**Tracked metrics** (in `_quiz_tracking.json`):
- Total agents taking quiz
- % passing on first try
- Average score
- Most commonly failed questions
- Time spent per attempt

**Used to**:
- Identify which rules need clearer docs
- Track onboarding effectiveness
- Improve ia-rules.md clarity over time

---

## 🎓 Learning Outcomes

After this quiz you will understand:
- ✅ Why ia-rules.md cannot be broken
- ✅ What thread isolation means (and why it matters)
- ✅ When to checkpoint and what to document
- ✅ Why ports > direct infrastructure access
- ✅ How to handle reality ≠ documentation

These 5 concepts prevent 80% of architectural failures.

---

**Ready?** Take the quiz, then continue with FIRST_SESSION_SETUP.md! 🚀
