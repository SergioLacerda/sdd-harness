# 🎯 Onboarding Guide — Welcome to RPG Narrative Server

This folder contains everything you need to get oriented as a new agent on this codebase.

## 📋 What's Here

```
onboarding/
├── README.md (you are here)
├── VALIDATION_QUIZ.md (5-question mandatory quiz on ia-rules.md)
└── (future: role-specific onboarding guides)
```

## 🚀 YOUR FIRST 20 MINUTES

**Follow this in order:**

### 1️⃣  START HERE: `/docs/ia/guides/FIRST_SESSION_SETUP.md`
- 20 min total
- Reads MASTER_INDEX → ia-rules → QUIZ → QUICK_START
- Ends with you ready to code

### 2️⃣  TAKE THE QUIZ: `VALIDATION_QUIZ.md`
- 5-10 minutes
- 5 questions on ia-rules.md
- Need ≥80% (4/5) to pass

### 3️⃣  IF YOU PASSED:
- Continue with FIRST_SESSION_SETUP.md (rest of sections)
- Choose your PATH (A/B/C/D)
- Load context

### 4️⃣  IF YOU FAILED:
- ❌ Stop here
- 📖 Re-read `/EXECUTION/spec/CANONICAL/rules/ia-rules.md` (10 min)
- ⏰ Wait 30 minutes
- 🔄 Retake quiz

---

## 📝 THE VALIDATION QUIZ

**What it covers**: 5 critical protocols from ia-rules.md

1. **Source of Truth Priority** (constitution.md)
2. **Thread Isolation** (mandatory, no cross-thread modifications)
3. **Checkpointing** (documentation must stay in sync)
4. **Ports** (never bypass, always use abstractions)
5. **Gap Documentation** (reality ≠ docs is normal, document it)

**Why mandatory?**
- These 5 prevent 80% of architectural failures
- Can't start work without understanding them
- Forces rules into working memory before you code

**Format options**:

**For Humans**:
```
1. Open: /docs/ia/guides/onboarding/VALIDATION_QUIZ.md
2. Answer 5 questions (A/B/C/D)
3. Self-score (need ≥80%)
4. If passed: continue
   If failed: re-read ia-rules.md, retry in 30 min
```

**For AI Agents**:
```bash
python /docs/ia/scripts/validate_quiz.py
```
- Runs 5 questions interactively
- Logs result automatically
- Tells you immediately if passed
- Score logged to analytics file

---

## 📊 Quiz Tracking

Your quiz attempts are logged to:
```
/docs/ia/REALITY/current-system-state/_quiz_tracking.json
```

**What's tracked**:
- Session ID
- Timestamp
- Score & percentage
- Pass/fail
- Attempt number
- Time taken
- Which questions you got wrong

**Used for**:
- Identifying which concepts need clearer docs
- Measuring onboarding effectiveness
- Improving ia-rules.md over time

---

## 🎓 Learning Path

```
START
  ↓
Read FIRST_SESSION_SETUP.md (0-20 min)
  ├─ MASTER_INDEX
  ├─ ia-rules.md (LOCKED IN)
  └─ ⏸️ VALIDATION QUIZ (5-10 min)
  ↓
PASS? (≥80%)
  ├─ YES → Continue (pick PATH, load context)
  └─ NO  → Re-read ia-rules, wait 30 min, retry
  ↓
Pick your work PATH (A/B/C/D)
  ↓
Load adaptive context (only what you need)
  ↓
Read domain-specific specs
  ↓
Implement! 🚀
```

---

## ⚡ Quick Reference

| Question | Answer |
|----------|--------|
| I'm confused about the rules | Read ia-rules.md (whole doc) |
| I want to know architecture WHY | Read decisions/ADR-*.md |
| I want to know current state | Read current-system-state/ |
| I want to know what goes where | Read specs/_INDEX_BY_DOMAIN.md |
| I'm about to implement feature | Read specs/_shared/feature-checklist.md |
| I'm testing my code | Read specs/_shared/testing.md |
| I'm about to merge | Read specs/_shared/definition_of_done.md |

---

## 🤔 Common Questions

**Q: Do I have to take the quiz?**
A: Yes, it's mandatory. Non-negotiable. These 5 concepts prevent 80% of failures.

**Q: What if I fail the quiz?**
A: Re-read ia-rules.md, wait 30 min, try again. It's designed to be passable if you read the docs.

**Q: Can I skip to coding without onboarding?**
A: Not recommended. 20 minutes now saves 2+ hours of rework later.

**Q: How long does all this take?**
A: 20 min onboarding + quiz. Most people pass on first try (≥80% pass rate target).

**Q: What if I'm experienced with the codebase?**
A: Take the quiz anyway. Rules may have changed. Keeps everyone in sync.

---

## 📞 Getting Help

**If quiz questions are unclear:**
- Question text unclear? → Report it (include which question)
- Answer not in ia-rules.md? → It should be. This is a bug. Report it.
- Disagreeing with a correct answer? → Read the explanation + reference

**If you're stuck:**
- Stuck in quiz → Re-read that section of ia-rules.md
- Don't understand ia-rules.md? → Read constitution.md (philosophical foundation)
- Still stuck → ASK (don't guess)

---

## 🚀 Next Steps

1. **Just landed here?** → Read FIRST_SESSION_SETUP.md (20 min)
2. **Taking the quiz?** → Open VALIDATION_QUIZ.md or run Python script
3. **Ready to work?** → Go to guides/QUICK_START.md and pick your PATH
4. **Want to understand why?** → Read decisions/ADR-*.md

---

**Created**: 2026-04-18
**Last Updated**: 2026-04-18
**Onboarding Score**: 9.5/10 (validation added!)
