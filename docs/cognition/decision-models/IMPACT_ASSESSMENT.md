# Decision Model: Impact Assessment

**Purpose:** Before touching any code, evaluate the blast radius of the change. Small underestimations here cause large incidents.

---

## 📐 The 3-Dimension Assessment

For every change, score each dimension from 1 (low) to 3 (high):

| Dimension | 1 (Low) | 2 (Medium) | 3 (High) |
|---|---|---|---|
| **Breadth** | 1 file/function | 1 module | Cross-module/package |
| **Depth** | Isolated logic | Shared utility | Core abstraction / public API |
| **Reversibility** | Easy git revert | Requires migration | Data mutation / irreversible |

**Total Score:**

- 3–4: Proceed with PATH A or B
- 5–6: Proceed with PATH C, write ADR if score = 6
- 7–9: **STOP. Escalate. Re-scope or get architecture review.**

---

## 🔍 Blast Radius Checklist

Before implementing, answer:

- [ ] Which tests would break if I'm wrong?
- [ ] What downstream consumers depend on what I'm changing?
- [ ] Is there a database schema, serialization format, or wire protocol affected?
- [ ] Can I roll this back in under 5 minutes?

---

## 🛡️ Safe Change Principles

### Expand-Contract Pattern (for API changes)

Never remove or modify a public interface in a single step:

1. **Expand**: Add the new version alongside the old
2. **Migrate**: Move all consumers to the new version
3. **Contract**: Remove the old version

### Feature Flags (for risky features)

If impact score ≥ 6, wrap in a feature flag before deploying to production.

---

## References

- Classification: [`TASK_CLASSIFICATION.md`](./TASK_CLASSIFICATION.md)
- Complex PATH: [`runtime/paths/PATH_C_COMPLEX_FEATURE.md`](../../runtime/paths/PATH_C_COMPLEX_FEATURE.md)
