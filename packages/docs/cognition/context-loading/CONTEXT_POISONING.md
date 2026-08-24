# Context Management: Conflict & Poisoning

**Purpose:** Prevent stale, conflicting, or irrelevant documentation from confusing the agent's logic.

---

## ☣️ What is Context Poisoning?

It occurs when the agent loads two or more pieces of information that contradict each other, leading to hallucinations, indecision, or incorrect implementation.

### Common Sources

1. **The `_OLD` Residue**: Loading files with `OLD_` or `_v2` prefixes alongside the current version.
2. **Implementation vs. Spec Gap**: Loading a "reality" audit that says a feature is broken while the "canonical" spec says it works.
3. **Cross-Project Bleed**: Loading templates from other projects that use different naming conventions.

---

## 🛡️ Poisoning Prevention Rules

### Rule 1: Single Source of Truth (SSOT)

Always prioritize `spec/canonical/` over any other directory. If a guide contradicts the canonical spec, the spec wins.

### Rule 2: Temporal Filtering

Never load "Archive" or "History" directories during execution PATHs. They are for research only.

### Rule 3: The "Reality" Check

When loading `spec/reality/` (audits/analyses), use it ONLY to identify bugs. Do NOT use it as a pattern for new code. Patterns must come from `spec/canonical/`.

---

## 💉 The Antidote: Context Flushing

If the agent becomes confused or starts hallucinating:

1. **Flush**: Clear the current context window completely.
2. **Audit**: Identify the conflicting files (usually via `grep` or checking filenames).
3. **Re-load**: Follow the PATH routing strictly, ensuring no "extra" files are pulled in.

---

## 🔍 Spotting Poisoning

Watch for these agent behaviors:

- "I will implement X... but the documentation says Y, so I will do Z."
- Constantly switching between two different naming conventions for the same variable.
- Referencing files or directories that were recently deleted/renamed (Residual Memory).

---

## 📏 Rule
>
> **Less is Safer.** If you aren't 100% sure a file is needed for the current step, don't load it. You can always pull it in later if a gap is discovered.

---

## References

- Anti-pattern: [`SYMPTOM_FIXING.md`](../anti-patterns/SYMPTOM_FIXING.md)
- Routing: [`path-routing.md`](./path-routing.md)
