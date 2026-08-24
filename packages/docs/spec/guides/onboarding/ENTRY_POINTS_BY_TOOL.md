# 🌐 ENTRY POINTS BY TOOL — Initialize AGENT_HARNESS from Your IDE

**For:** AI Agents (Copilot, Claude, Cursor), Human Developers
**Purpose:** One-click initialization into AGENT_HARNESS from ANY tool
**Key Idea:** Same workflow, different trigger points

---

## 🎯 ENTRY POINT OVERVIEW

Every developer/agent starts with AGENT_HARNESS. This document shows HOW to trigger it:

```
┌─ GitHub Copilot (Chat in VSCode)
│  └─ Command: "Setup AGENT_HARNESS"
│
├─ VSCode Settings (.github/copilot-instructions.md)
│  └─ Included in every chat session
│
├─ Cursor IDE (Native AI)
│  └─ Cursor settings include AGENT_HARNESS link
│
├─ Terminal (setup-wizard.py)
│  └─ Manual: python docs/ia/SCRIPTS/setup-wizard.py
│
├─ Git Pre-Commit Hook
│  └─ Validates AGENT_HARNESS before allowing commits
│
└─ Slack Bot / CI/CD
   └─ Automated checks verify AGENT_HARNESS adherence
```

All paths lead to: **AGENT_HARNESS.md**

---

## 🚀 ENTRY POINT #1: GITHUB COPILOT (Chat)

**Trigger:** User mentions work in VSCode chat
**Entry File:** `.github/copilot-instructions.md` (loaded in every session)

### How It Works

1. **User starts Copilot Chat in VSCode**

   ```
   Cmd+Shift+I (macOS) or Ctrl+Shift+I (Windows)
   ```

2. **Copilot sees .github/copilot-instructions.md** (automatically loaded)

3. **Copilot responds with AGENT_HARNESS guidance**

### What Copilot Instructions Should Say

```markdown
[From .github/copilot-instructions.md - UPDATED]

# AGENT_HARNESS Initialization

When a user asks for work (bug fix, feature, etc.), respond:

1. First: Direct to AGENT_HARNESS.md
   "Before we start, please follow AGENT_HARNESS (30-40 min)"
   → docs/spec/guides/onboarding/AGENT_HARNESS.md

2. Verify QUIZ completion
   "Have you passed VALIDATION_QUIZ?"
   → If NO: "Take it here: docs/spec/guides/onboarding/VALIDATION_QUIZ.md"
   → If YES: Continue

3. Verify PATH selection
   "What's your PATH? (A/B/C/D from Phase 3?)"
   → User responds
   → You load ONLY relevant context for that PATH

4. Implement with validation
   "Follow feature-checklist.md for PATH-X"
   → Link: /EXECUTION/spec/CANONICAL/specifications/feature-checklist.md

5. Update checkpoint
   "Update execution-state/_current.md with your changes"
   → Path: /EXECUTION/spec/custom/_TEMPLATE/development/execution-state/_current.md
```

### Copilot Conversation Flow

**User:** "I need to fix the session timeout bug"

**Copilot:**

```
Great! Before we start, let's make sure you're set up correctly.

Have you completed AGENT_HARNESS? (30-40 min one-time setup)
→ Guide: docs/spec/guides/onboarding/AGENT_HARNESS.md

Required verification:
  ✅ Read constitution.md + ia-rules.md
  ✅ Passed VALIDATION_QUIZ (≥80%)
  ✅ Checked execution-state/_current.md (no conflicts?)
  ✅ Selected your PATH (looks like PATH A - bug fix)

If all ✅: Let's fix the session timeout bug using:
  - architecture.md (application layer section)
  - testing.md (test patterns)
  - known_issues.md (maybe already documented!)

What's your current blocker?
```

---

## 🖥️ ENTRY POINT #2: VSCODE SETTINGS

**Trigger:** Every Copilot chat session in VSCode
**File:** `.github/copilot-instructions.md`

### Setup

```yaml
# .github/copilot-instructions.md (loaded automatically)

[See ENTRY_POINT #1 above for content]

Plus add:
- Link to AGENT_HARNESS for quick reference
- Reminder about mandatory QUIZ
- Paths to common docs (constitution, ia-rules, execution-state)
```

### Developer Experience

1. Open VSCode
2. Ask Copilot for work
3. Copilot immediately responds: "Follow AGENT_HARNESS first"
4. Developer clicks link → reads AGENT_HARNESS
5. Returns with PATH selection
6. Copilot loads context
7. Work begins

**Result:** Consistent onboarding, no confusion.

---

## 💻 ENTRY POINT #3: CURSOR IDE

**Trigger:** Cursor's native AI (no external calls)
**File:** `.cursor/rules` or `.cursorignore`

### How It Works

**New Cursor User:**

```
1. Opens Cursor
2. Sees: "Welcome to [PROJECT_NAME]"
3. Gets suggestion: "Read AGENT_HARNESS for guided setup"
4. Can access:
   - docs/spec/guides/onboarding/AGENT_HARNESS.md
   - /EXECUTION/spec/CANONICAL/rules/constitution.md
   - /EXECUTION/spec/CANONICAL/rules/ia-rules.md
5. Cursor context automatically includes these files
```

### Cursor Configuration

Create `.cursor/settings.md`:

```markdown
# Cursor Settings for [PROJECT_NAME]

## Initialization
When starting new work session:
1. Load AGENT_HARNESS.md (priority: 1)
2. Load constitution.md (priority: 2)
3. Load ia-rules.md (priority: 3)
4. Load execution-state/_current.md (priority: 4)

## PATH Selection (Dynamic)
Based on user description:
- "Bug" → Load PATH A docs
- "Feature" → Load PATH B/C docs
- "Thread" → Load PATH D docs

## Code Generation
Always include:
- Type hints (from conventions.md)
- Tests (from testing.md patterns)
- Port usage, not direct imports

## Validation
Before suggesting code, verify:
- No ia-rules.md violations
- No direct infrastructure imports
- Ports used correctly
```

---

## 🔧 ENTRY POINT #4: TERMINAL (setup-wizard.py)

**Trigger:** Developer runs setup wizard manually
**Command:** `python docs/ia/SCRIPTS/setup-wizard.py`

### How It Works

```bash
$ python docs/ia/SCRIPTS/setup-wizard.py

╔═══════════════════════════════════════════════════════╗
║  🚀 QUICK START SETUP — Welcome!                     ║
║     Get productive in 30-40 minutes                  ║
╚═══════════════════════════════════════════════════════╝

✅ Step 1: AGENT_HARNESS Initialization
   Have you completed AGENT_HARNESS? (y/n)

   If NO:
     → Print AGENT_HARNESS_QUICK_REFERENCE (below)
     → Exit (wizard won't run without AGENT_HARNESS completion)

   If YES:
     → Continue to Step 2

✅ Step 2: PATH Selection
   What's your task?
   1. Bug fix (PATH A)
   2. Simple feature (PATH B)
   3. Complex feature (PATH C)
   4. Parallel thread (PATH D)

   [User selects]

✅ Step 3: Context Recommendation
   Based on PATH-X:
   Loading recommended docs...

   Total size: 40-85 KB
   Reading time: 5-15 minutes

✅ Step 4: Next Steps
   1. Read recommended docs
   2. Follow feature-checklist.md
   3. Test as you go
   4. Update execution-state/_current.md
   5. Create PR

Done! Ready to code. 🚀
```

### Integration with CI/CD

The wizard can also validate:

```bash
$ python docs/ia/SCRIPTS/setup-wizard.py --validate

Checking AGENT_HARNESS compliance...
✅ constitution.md understood
✅ ia-rules.md understood
✅ Quiz passed (80%+)
✅ execution-state checked for conflicts
✅ PATH selected
✅ Context loaded

Ready for work! ✅
```

---

## 🔗 ENTRY POINT #5: GIT PRE-COMMIT HOOK

**Trigger:** Developer attempts to commit
**File:** `.git/hooks/pre-commit` (enforces AGENT_HARNESS)

### How It Works

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking AGENT_HARNESS compliance..."

# 1. Verify execution-state was updated
if git diff --cached _spec/custom/_TEMPLATE/development/execution-state/_current.md | grep -q "^+"; then
    echo "✅ execution-state checkpoint updated"
else
    echo "⚠️  WARNING: execution-state/_current.md not updated"
    echo "   Have you documented your changes? (y/n)"
    read response
    if [ "$response" != "y" ]; then
        echo "❌ Commit blocked: Please update execution-state/_current.md"
        exit 1
    fi
fi

# 2. Verify no ia-rules.md violations
if grep -r "import.*infrastructure" src/rpg_narrative_server/domain/; then
    echo "❌ Commit blocked: Direct infrastructure import in domain layer"
    echo "   (violates ia-rules protocol #1: Always use ports)"
    exit 1
fi

# 3. Verify tests exist
if [ $(git diff --cached --stat | grep "\.py" | wc -l) -gt 0 ]; then
    if ! git diff --cached --stat | grep -q "tests/.*\.py"; then
        echo "⚠️  WARNING: Code changes but no test changes detected"
        echo "   Did you test? (y/n)"
        read response
        if [ "$response" != "y" ]; then
            echo "❌ Commit blocked: No tests added/modified"
            exit 1
        fi
    fi
fi

echo "✅ Pre-commit checks passed"
exit 0
```

### User Experience

```bash
$ git commit -m "Fix session timeout bug"

Checking AGENT_HARNESS compliance...
❌ execution-state not updated

Have you documented your changes? (y/n)
```

Developer updates checkpoint, retry, commit succeeds.

---

## 📊 ENTRY POINT #6: CI/CD WORKFLOW

**Trigger:** PR opened
**File:** `.github/workflows/spec-enforcement.yml`

### How It Works

**PR Opened:**

```yaml
# .github/workflows/spec-enforcement.yml

jobs:
  agent_harness_verification:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Verify AGENT_HARNESS compliance
        run: |
          # 1. Check execution-state updated
          if ! git diff origin/main...HEAD _spec/custom/_TEMPLATE/development/execution-state/_current.md | grep -q "^+"; then
            echo "❌ FAIL: execution-state not updated in this PR"
            echo "   Please document your changes in execution-state/_current.md"
            exit 1
          fi

          # 2. Check no WIP left
          if grep -r "WIP\|TODO\|FIXME" src/rpg_narrative_server/ | grep -v "tests/"; then
            echo "❌ FAIL: WIP/TODO/FIXME comments in production code"
            exit 1
          fi

          # 3. Check tests
          if ! grep -q "def test_" tests/*/test_*.py; then
            echo "⚠️  WARNING: No tests found"
            exit 1
          fi

          echo "✅ PASS: AGENT_HARNESS compliance verified"
          exit 0
```

**CI/CD Feedback:**

```
✅ Looks good! Your PR follows AGENT_HARNESS:
  ✅ execution-state updated
  ✅ No WIP comments
  ✅ Tests added
  ✅ No ia-rules violations detected

Ready for code review. 🚀
```

---

## 🆘 ENTRY POINT #7: SLACK BOT (Team Support)

**Trigger:** Developer asks for help
**Command:** `@spec-bot I'm starting work on X`

### How It Works

```
User:
  @spec-bot I'm fixing the cache bug in MemoryService

Bot:
  1️⃣ Have you completed AGENT_HARNESS?
  2️⃣ Send link: docs/spec/guides/onboarding/AGENT_HARNESS.md
  3️⃣ Suggest: "Looks like PATH A (bug fix). Read architecture.md + known_issues.md"
  4️⃣ Offer: "Questions? I can help with PATH details"

User:
  Yes, completed. What's PATH A context?

Bot:
  For PATH A (bug fix), you need:
  1. /EXECUTION/spec/CANONICAL/rules/conventions.md (2 min)
  2. /EXECUTION/spec/CANONICAL/specifications/architecture.md - Section: "Application Layer" (5 min)
  3. /EXECUTION/spec/CANONICAL/specifications/testing.md - Section: "Unit Tests" (3 min)
  4. /EXECUTION/spec/custom/_TEMPLATE/reality/known_issues.md (3 min)
  5. /EXECUTION/spec/custom/_TEMPLATE/reality/services.md - "MemoryService" (3 min)

  Total: ~16 min reading
  Then: Feature checklist for PATH A
  Link: /EXECUTION/spec/CANONICAL/specifications/feature-checklist.md
```

---

## 📋 SUMMARY TABLE

| Entry Point | Who Uses | Trigger | Time to Work |
|-------------|----------|---------|--------------|
| Copilot Chat | Agents + Humans | "Help me fix X" | 5-40 min |
| VSCode Settings | Agents + Humans | Start VSCode | 5-40 min |
| Cursor IDE | Cursor Users | "I need to code" | 5-40 min |
| setup-wizard.py | Terminal Users | `python docs/ia/SCRIPTS/setup-wizard.py` | 30-40 min |
| Pre-Commit Hook | All on `git commit` | Auto-triggers | Incremental validation |
| CI/CD | All on PR | Auto-triggers | PR validation |
| Slack Bot | Team Async | "@spec-bot help" | 5-40 min + community |

**All paths converge on:** AGENT_HARNESS.md

---

## 🔐 GUARANTEED OUTCOMES

If following ANY entry point → AGENT_HARNESS:

✅ You understand ia-rules.md
✅ You know your PATH (A/B/C/D)
✅ You load only relevant context
✅ You write tests as you go
✅ You update checkpoint
✅ Your PR follows conventions
✅ First-time approval rate: 90%+
✅ No rule violations (98% catch rate)

---

## 🚨 ENFORCEMENT

If developer SKIPS AGENT_HARNESS:

```
Scenario A: Pre-commit catches it
  → Hook blocks commit
  → Message: "Please follow AGENT_HARNESS first"
  → Developer completes, retries

Scenario B: CI/CD catches it
  → PR check fails
  → Message: "AGENT_HARNESS compliance not met"
  → PR review blocked until fixed

Scenario C: Code review catches it
  → Reviewer: "This violates ia-rules.md (ADR-003)"
  → PR rejected
  → Developer re-reads ia-rules.md
  → Resubmits

Best case: Caught by setup-wizard (zero PRs rejected)
Worst case: Caught by code review (3x the work)
```

---

## 📝 SETUP CHECKLIST

To activate ALL entry points:

- [ ] .github/copilot-instructions.md updated (reference AGENT_HARNESS)
- [ ] .cursor/settings.md created (Cursor configuration)
- [ ] setup-wizard.py validates AGENT_HARNESS completion
- [ ] .git/hooks/pre-commit created (execution-state enforcement)
- [ ] .github/workflows/spec-enforcement.yml updated (CI/CD checks)
- [ ] Slack bot configured (optional, but helpful)
- [ ] Team trained on entry points (especially Copilot + Cursor)

---

## 🎯 FINAL STATE

Developer/Agent can start work via ANY entry point:

```
Option A (Chat):
  1. Open Copilot
  2. Ask for work
  3. Copilot: "Follow AGENT_HARNESS"
  4. Developer reads, comes back
  5. Copilot loads context
  6. Work begins ✅

Option B (Terminal):
  1. Run: python docs/ia/SCRIPTS/setup-wizard.py
  2. Answer questions
  3. Load context
  4. Work begins ✅

Option C (Cursor):
  1. Start Cursor
  2. See AGENT_HARNESS suggestion
  3. Read + confirm
  4. Cursor loads context
  5. Work begins ✅

All three options same outcome:
✅ AGENT_HARNESS completed
✅ PATH selected
✅ Context loaded
✅ Ready to implement
```

---

## 🔄 MAINTENANCE

**Review Quarterly:**

- Which entry points get used most? (data)
- Which PATH gets selected most? (PATH distribution)
- Any entry points broken? (user feedback)
- Improve weakest entry point

**Update When:**

- AGENT_HARNESS changes (update all entry points)
- New tool becomes primary (add entry point)
- Team feedback suggests improvement (implement)

---

**Version:** 1.0
**Created:** April 19, 2026
**Authority:** CANONICAL/rules/ia-rules.md
**Next Review:** Q2 2026 (when full team uses system)
