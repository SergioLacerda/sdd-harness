# 🎟️ SESSION QUICK REFERENCE CARD

**Print/Keep this handy during your work session**

---

## 🏗️ TWO LAYERS OF DOCUMENTATION

### 🔒 GOVERNANCE (Immutable — Stable)
**See**: [GOVERNANCE_RULES.md](../GOVERNANCE_RULES.md)

```
What's permanent:
  ✓ ia-rules.md (16 protocols - DON'T BREAK)
  ✓ constitution.md (principles)
  ✓ architecture.md (patterns)
  ✓ conventions.md (style)

These RARELY change. They're the stable foundation.
```

### 🔄 RUNTIME (Mutable — Changing)
**See**: [RUNTIME_STATE.md](../RUNTIME_STATE.md)

```
What's current:
  ✓ execution_state.md (what's happening NOW)
  ✓ known_issues.md (bugs found TODAY)
  ✓ current-system-state/ (reality vs ideal)

These CHANGE constantly. Update as you work.
```

**Key**: Gap between governance and runtime is NORMAL.
- Governance = ideal ("What should be?")
- Runtime = reality ("What actually is?")
- Document gaps, don't assume governance is wrong

---

## 🔴 RULES YOU CAN'T BREAK (ia-rules.md)

```
1. Never bypass ports (always use the abstraction)
2. Never access infrastructure directly
3. Vector index is NOT source of truth
4. Don't mix decisions from multiple threads
5. Follow "Next Actions" strictly from execution_state.md
6. No implicit state assumptions
7. Always check execution_state.md before action
8. Thread isolation mandatory (if multi-thread)
9. Checkpointing required after changes
10. No blocking operations (async-first)
11. Propagate errors, don't swallow them
12. Ask if unclear, never guess
13. Documentation as source of truth
14. Follow constitution.md principles
15. Naming & conventions from conventions.md
16. Testing patterns from testing.md
```

---

## 📍 STARTUP SEQUENCE (15 minutes)

```
[ ] 1-2min: Read MASTER_INDEX.md
[ ] 3-5min: Read ia-rules.md (LOCK YOURSELF)
[ ] 6-8min: Read QUICK_START.md (choose PATH)
[ ] 9-12min: Read execution_state.md (check conflicts)
[ ] 13-15min: Load current-system-state/ files (your PATH only)

RESULT: Ready to implement ✓
```

---

## 🎯 PATH QUICK LOOKUP

| PATH | Use For | Time | Context | Files to Load |
|------|---------|------|---------|---------------|
| **A** | Bug fix | 1.5h | ~45KB | known_issues.md + services.md |
| **B** | Simple feature (1-2 layers) | 2h | ~55KB | contracts.md + data_models.md |
| **C** | Complex (3+ layers) | 3-4h | ~100KB | rag_pipeline.md + services.md + contracts.md |
| **D** | Multi-thread parallel | Variable | Isolated | threading_concurrency.md + known_issues.md |

---

## 📚 ESSENTIAL DOCUMENTS

**Phase 1 - Always (non-negotiable)**
```
✓ /EXECUTION/spec/CANONICAL/rules/ia-rules.md (16 rules)
✓ /EXECUTION/spec/CANONICAL/rules/constitution.md (principles)
✓ /docs/ia/DEVELOPMENT/execution-state/_current.md (current state)
```

**Phase 2 - Your PATH (choose one)**
```
PATH A: feature-checklist.md (Layer 5+, affected layer only)
PATH B: feature-checklist.md (Layers 1-3)
PATH C: feature-checklist.md (ALL layers)
PATH D: runtime/threads/TEMPLATE.md (thread format)
```

**Phase 3 - Before Merge (mandatory)**
```
✓ /EXECUTION/spec/CANONICAL/specifications/definition_of_done.md
✓ /docs/ia/DEVELOPMENT/execution-state/_current.md (update checkpoint)
```

---

## 🚨 MISTAKES TO AVOID

| ❌ Mistake | ✅ Fix |
|-----------|--------|
| Skip ia-rules.md | Read it FIRST (non-negotiable) |
| Load all context (150KB+) | Load ONLY your PATH files (~45KB max) |
| Guess system state | Always check execution_state.md |
| Ignore known_issues.md | Prevents repeating same bug |
| Bypass ports | Always use port abstraction |
| Silent error handling | Propagate errors up |
| Multi-thread conflict | Check execution_state.md before action |
| Assume global state | No implicit state |

---

## 📍 WHERE THINGS ARE

```
/docs/ia/
├── ia-rules.md ⭐ (LOCK YOURSELF HERE)
├── MASTER_INDEX.md (navigation root)
│
├── guides/
│   ├── FIRST_SESSION_SETUP.md (orientation)
│   ├── QUICK_START.md (3-min PATH choice)
│   ├── INDEX.md ("I need X...")
│   └── ... (more)
│
├── specs/
│   ├── constitution.md (principles)
│   ├── _shared/
│   │   ├── feature-checklist.md (8-layer)
│   │   ├── testing.md (test patterns)
│   │   └── definition_of_done.md (merge criteria)
│   └── runtime/
│       └── execution_state.md (current state)
│
└── current-system-state/
    ├── _INDEX.md (query router)
    ├── known_issues.md (bugs + edge cases)
    ├── rag_pipeline.md (real RAG flow)
    ├── services.md (8 services)
    ├── contracts.md (9 ports)
    ├── data_models.md (DTOs)
    ├── storage_limitations.md (5 constraints)
    ├── threading_concurrency.md (5 limits)
    └── scaling_constraints.md (5 bottlenecks)
```

---

## ⚡ QUICK CHECKLIST FOR IMPLEMENTATION

Before writing code:
```
[ ] Identified which port(s) I'll use
[ ] Read port contract in contracts.md
[ ] Verified no conflicts in execution_state.md
[ ] Checked known_issues.md (not repeating bug?)
[ ] Determined which layer I'm in
[ ] Confirmed naming conventions
```

During implementation:
```
[ ] Following feature-checklist.md layer process
[ ] Using test patterns from testing.md
[ ] Respecting port boundaries
[ ] No blocking operations (async-first)
[ ] Error handling propagates (not swallows)
```

After implementation:
```
[ ] All tests pass (testing.md patterns)
[ ] Code review against definition_of_done.md
[ ] Updated execution_state.md (checkpoint)
[ ] Flagged any open questions
[ ] Marked checkpoint complete
```

---

## 📞 WHEN TO ASK VS WHEN NOT TO ASK

**ASK if:**
```
[ ] Rules conflict (two ia-rules contradict)
[ ] Unclear which PATH applies
[ ] Active threads in your area (execution_state shows conflict)
[ ] Known_issues.md doesn't cover your situation
[ ] Design decision not documented
[ ] Uncertain about port boundaries
[ ] Multiple possible correct approaches
```

**DO NOT ASK if:**
```
[ ] Answer is in ia-rules.md
[ ] Answer is in QUICK_START.md
[ ] Answer is in feature-checklist.md
[ ] Answer is in your PATH guide
[ ] Answer is in definition_of_done.md
```

---

## 🎯 SESSION END CHECKLIST

Before finishing session:
```
[ ] Updated /docs/ia/DEVELOPMENT/execution-state/_current.md
    - Documented what you did
    - Flagged open questions
    - Recorded risks
    - Marked thread status (if PATH D)

[ ] Code passes all tests

[ ] Definition of done checklist ✓

[ ] No regressions in related areas

[ ] If multi-thread (PATH D):
    - Only touched your thread
    - Didn't modify global architecture
    - Checkpoint complete
```

---

## 🔗 IMPORTANT LINKS

**One-stop shortcuts:**
- Start: `/docs/ia/MASTER_INDEX.md`
- Rules: `/EXECUTION/spec/CANONICAL/rules/ia-rules.md` ← LOCK HERE
- Setup: `/docs/ia/guides/FIRST_SESSION_SETUP.md`
- PathChoice: `/docs/ia/guides/QUICK_START.md`
- State: `/docs/ia/DEVELOPMENT/execution-state/_current.md`
- Queries: `/docs/ia/REALITY/current-system-state/_INDEX.md`

---

**Remember: Documentation is source of truth. When uncertain, refer to docs, don't guess. 🎯**
