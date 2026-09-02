# Anti-Pattern: Cognitive Overload

**Also known as:** Context Flooding, "Let me read everything first"

---

## ❌ The Problem

Loading the entire documentation before starting a task. The agent/developer convinces themselves that more context = better decisions.

**Reality:** More context = slower decisions + higher token cost + loss of focus on the actual problem.

### Symptoms

- Loading full `spec/` for a bugfix
- Reading unrelated ADRs before a simple feature
- "I'll just understand the whole system first"
- Spending 30+ minutes on research for a 10-minute change

### Why it happens

- Fear of missing context that turns out to be relevant
- Lack of trust in the PATH classification system
- No clear entry point defined

---

## ✅ The Cure

**Use the PATH system.** It tells you exactly what to load and nothing more.

```
PATH A (bugfix) → 1 layer of spec/canonical + affected module only
PATH B (simple) → spec/canonical core + 1 guide
PATH C (complex) → full spec (this is the ONLY justified case)
```

**Rule:** If you're not on PATH C, you should NOT be loading full documentation.

**The test:** Can you describe what you need in one sentence? If yes, you only need context for that one thing.

---

## 📏 Benchmark

A correctly scoped context load takes < 2 minutes.
If you're still loading context after 5 minutes, you have cognitive overload.

---

## References

- Context loading strategy: [`cognition/context-loading/path-routing.md`](../context-loading/path-routing.md)
- Confidence model: [`cognition/decision-models/CONFIDENCE_THRESHOLD.md`](../decision-models/CONFIDENCE_THRESHOLD.md)
