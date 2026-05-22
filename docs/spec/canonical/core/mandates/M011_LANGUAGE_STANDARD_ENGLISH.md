# Mandate: English Language Standard

**ID:** M011
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** pre-execution, execution, post-execution

---

## Objective

Enforce a single language standard for engineering artifacts to prevent ambiguity,
mixed-language drift, and communication inconsistency across humans and agents.

---

## Requirements (MUST)

1. All source code identifiers and comments MUST be in English.
2. All technical documentation and governance artifacts MUST be in English.
3. Generated onboarding/agent entrypoint artifacts MUST be in English.
4. CLI help text and examples introduced by new changes MUST be in English.

---

## Prohibitions (NEVER)

1. Do not introduce mixed-language sections in the same technical artifact.
2. Do not add new Portuguese-only code comments, docs, or operational instructions.
3. Do not keep translated duplicates as canonical content.

---

## Limited Exceptions

1. User-provided free-text inputs may remain in the original language.
2. Proper nouns, legal names, and quoted external text may preserve original wording.
3. Historical legacy files may remain unchanged until explicitly migrated; all new
   edits in those files MUST follow this mandate.

---

## Validation Checklist

- [ ] New/updated code comments are in English.
- [ ] New/updated docs are in English.
- [ ] New/updated generated agent onboarding text is in English.
- [ ] No mixed-language operational instructions were introduced.

---

## Failure Mode

If a change introduces non-English technical content outside allowed exceptions,
delivery is `BLOCKED` until corrected.
