# Anti-Pattern: Scope Creep

**Also known as:** Feature Smuggling, "While I'm here...", Yak Shaving

---

## ❌ The Problem

Starting a scoped task and expanding it during execution — adding improvements, fixes, or features that weren't in the original scope.

### Symptoms

- "I noticed this other thing is broken, I'll fix it too"
- "While refactoring this function, I'll also redesign the interface"
- PR descriptions that say "also fixed X, Y, Z" (items not in the original ticket)
- Commits that mix `feat:`, `fix:`, and `refactor:` in a single change

### Why it's dangerous

- Untested side changes hide bugs
- Reviewers can't assess changes they didn't expect
- Rollbacks become expensive (the good change and bad change are tangled)
- It compounds: each new scope creep justifies the next one

---

## ✅ The Cure

**The Parking Lot Rule:** When you notice something else that needs fixing, write it down and park it. Do NOT fix it now.

```markdown
## 🅿️ Parking Lot (noticed during this task)
- [ ] Function X could be renamed for clarity → open new ticket
- [ ] Module Y has no tests → open new tech debt ticket
```

**One commit = one intent.**

Check before every commit:
> "Does this commit message describe ONE complete thought?"
> If not, split it.

### PATH Discipline

If you started on PATH A (bugfix) and find yourself changing a public API: **STOP. Re-classify to PATH C. Or park it.**

---

## 📏 Benchmark

A clean PATH A or B execution touches ≤ 3 files.
If you've touched > 5 files on a simple task, scope creep has already happened.

---

## References

- Impact assessment: [`cognition/decision-models/IMPACT_ASSESSMENT.md`](../decision-models/IMPACT_ASSESSMENT.md)
- PATH classification: [`cognition/decision-models/TASK_CLASSIFICATION.md`](../decision-models/TASK_CLASSIFICATION.md)
