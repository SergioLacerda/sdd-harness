# Anti-Pattern: Premature Execution

**Also known as:** Ready-Fire-Aim, "I'll figure it out as I go"

---

## ❌ The Problem

Starting implementation before understanding what success looks like. The agent or developer writes code first and defines correctness later.

### Symptoms
- No failing test written before the implementation
- "I'll add tests after I get it working"
- Unclear or absent acceptance criteria at the start
- Confidence score < 50% (see `CONFIDENCE_THRESHOLD.md`) but proceeding anyway
- Fixing compilation errors as the primary feedback loop (not test failures)

### Why it's dangerous
- You optimize for code that compiles, not code that's correct
- The definition of "done" shifts to match what was implemented (not what was needed)
- Technical debt is born in the first commit, not discovered later

---

## ✅ The Cure

**Always define "done" before writing implementation code.**

### Minimum viable pre-flight check:
1. Write the test first (even a placeholder)
2. Run it — confirm it FAILS for the right reason (RED)
3. Only then implement

```bash
# RED state — your contract with yourself
pytest tests/ -k "<your_feature>" -v
# FAILED: <reason that makes sense>
```

If you can't write a test because you don't know what to test:
→ Your confidence score is too low. Go back to context loading.

### The "Definition of Done" Contract
Before starting, answer in writing:
> "This task is complete when: ___"

If you can't fill in the blank with a measurable outcome, **stop and clarify**.

---

## 📏 Benchmark
On any PATH (A–F), you should be able to state the definition of done in ≤ 2 sentences before touching any file.

---

## References
- Confidence model: [`cognition/decision-models/CONFIDENCE_THRESHOLD.md`](../decision-models/CONFIDENCE_THRESHOLD.md)
- PATH A (correct approach): [`runtime/paths/PATH_A_BUGFIX.md`](../../runtime/paths/PATH_A_BUGFIX.md)
