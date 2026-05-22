# Anti-Pattern: Symptom Fixing

**Also known as:** Whack-a-Mole, Treating the Fever not the Infection

---

## ❌ The Problem

Applying fixes to the observable symptom without identifying and addressing the root cause. The bug keeps returning in different forms.

### Symptoms
- The same category of bug appears 2+ times in different places
- Fixes are applied with `try/except`, `if not None`, or null guards without understanding WHY the null/exception is happening
- Commit history shows: "fix X", then 2 days later "fix X again", then "fix X properly"
- Tests pass after the fix but the fix adds a special-case branch instead of eliminating the condition

### The Pattern (Anti)
```python
# ❌ Symptom fix — adding a guard without knowing why value is None
def process(value):
    if value is None:  # "fixed" — but WHY is value None?
        return
    ...
```

```python
# ✅ Root cause fix — the caller was not validating before calling
def get_value(source) -> Value:
    if not source.is_ready():
        raise ValueError("Source not ready — call only after initialization")
    return source.value
```

---

## ✅ The Cure

**The 5 Whys Protocol.** Before writing any fix, ask "why" five times:

```
Bug: NullPointerException in process()
Why? → value is None when passed to process()
Why? → the caller doesn't check if the object is ready
Why? → the caller assumes initialization is synchronous
Why? → the initialization was made async in a refactor 3 months ago
Why? → the refactor had no consumer impact analysis

Root Cause: async initialization without updating all consumers
Real Fix: add a readiness check in the public interface contract
```

### Test the Root Cause
Your fix is correct when:
1. You can write a test that targets the ROOT CAUSE (not the symptom)
2. That test fails BEFORE your fix
3. That test passes AFTER your fix
4. No special-case branches were added

---

## 📏 Benchmark
If your fix adds an `if/else` branch that exists solely to handle "the bug case":
→ You fixed a symptom. Find the root cause.

---

## References
- Impact assessment: [`cognition/decision-models/IMPACT_ASSESSMENT.md`](../decision-models/IMPACT_ASSESSMENT.md)
- PATH A (correct bugfix flow): [`runtime/paths/PATH_A_BUGFIX.md`](../../runtime/paths/PATH_A_BUGFIX.md)
