# M010 Git Safety Extension + G023 Creation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend M010 with a shared-state principle and complete git mutation rules, and create G023 as the first governance-category guideline covering operational git safety practices.

**Architecture:** Three source-of-truth files are modified directly (mandates.md, mandates.json, guidelines.dsl), then `sdd governance compile` + `sdd governance generate` regenerate all derived artifacts. No code changes — governance data only.

**Tech Stack:** SDD CLI (`sdd governance compile`, `sdd governance generate`, `sdd governance validate`), JSON, DSL (guidelines.dsl format)

**Design doc:** `.analysis/pending/2026-06-05-m010-git-safety-extension-design.md`

---

## Context

M010 in `mandates.json` already has a partial git entry:

```
enforcement_steps[-1]: "Confirm no git state-modifying command (`add`, `commit`, `push`,
  `reset`, `rebase`, `merge`) was executed without explicit human authorization..."
```

This plan:
- Adds the missing parallel agents / shared state principle (new concept, not in any file today)
- Expands the prohibited commands list (missing: `stash`, `cherry-pick`, `clean`, `checkout`, `switch`, `branch -D`)
- Aligns the human-readable `mandates.md` with what `mandates.json` already has (they are currently out of sync)
- Creates G023 in `guidelines.dsl` for operational git safety detail

---

## Task 1: Update M010 in `mandates.md`

**Files:**
- Modify: `.sdd/source/mandates/mandates.md:70-76`

The current M010 block (lines 70–76) reads:

```
## M010: Delivery Hygiene Enforcement

**Criticality**: high
**Customizable**: No

Every change must have explicit declared scope before execution. AI agents must
diagnose root cause before modifying any file. Scope expansion beyond the declared
task requires explicit user approval and stops current execution. Generated code
must be validated by tests, linting, and type checking before acceptance.
AI-specific violations that block delivery: prompt-to-code without diagnosis
(fixes symptoms, misses root cause), scope drift (silent expansion of affected
area), hallucinated architecture (inventing conventions or commands without
evidence), unvalidated generated code (merging without CI gate).
```

**Step 1: Open `.sdd/source/mandates/mandates.md` and locate line 75** (the long description paragraph for M010).

**Step 2: Replace the M010 description paragraph** with the expanded version:

```
Every change must have explicit declared scope before execution. AI agents must
diagnose root cause before modifying any file. Scope expansion beyond the declared
task requires explicit user approval and stops current execution. Generated code
must be validated by tests, linting, and type checking before acceptance.

Shared state assumption: agents must assume that other agents, threads, developers,
editors, or automated processes may be working in the same repository concurrently.
Uncommitted changes, branch pointers, stash entries, and index state must be
treated as potentially belonging to parallel work. Any action that mutates
repository state carries risk of disrupting concurrent work and requires the same
deliberateness as scope-expanding changes.

AI-specific violations that block delivery: prompt-to-code without diagnosis
(fixes symptoms, misses root cause), scope drift (silent expansion of affected
area), hallucinated architecture (inventing conventions or commands without
evidence), unvalidated generated code (merging without CI gate), git mutation
without approval (executing state-mutating git commands — commit, stash, push,
reset, rebase, merge, cherry-pick, clean, checkout, switch, branch -D — without
explicit per-command user authorization; read-only commands such as status, diff,
log, show are always permitted; approval for one command does not authorize others).
```

**Step 3: Verify the section looks correct**

Read back lines 70–90 to confirm the structure is intact (`## M010:` header, criticality/customizable fields, expanded paragraph).

---

## Task 2: Update M010 in `mandates.json`

**Files:**
- Modify: `.sdd/spec/mandates.json` (M010 object)

**Step 1: Open `.sdd/spec/mandates.json`** and locate the M010 object.

**Step 2: Update the `rationale` field** — append the shared state principle to the existing rationale text:

Current ending:
```
"...Task completion is NOT authorization\nfor committing — these are independent lifecycle events."
```

Append after that sentence:
```
\n\nShared state assumption: other agents, threads, developers, editors, or automated\nprocesses may be working in the same repository concurrently. Uncommitted changes,\nbranch pointers, stash entries, and index state must be treated as potentially\nbelonging to parallel work. Any mutation of repository state must be treated with\nthe same deliberateness as scope-expanding changes.
```

**Step 3: Replace the last `enforcement_steps` entry** — the current entry covers only 6 commands. Replace it with the complete list:

Current:
```json
"Confirm no git state-modifying command (`add`, `commit`, `push`, `reset`, `rebase`, `merge`) was executed without explicit human authorization in the current message"
```

Replace with:
```json
"Confirm no git state-mutating command (add, commit, push, reset, rebase, merge, stash, stash apply, stash pop, cherry-pick, clean, checkout, switch, branch -D) was executed without explicit per-command user authorization; assume parallel agents may be working in the same repository"
```

**Step 4: Replace the last `validation` entry** — current entry only mentions "authorization". Replace with:

Current:
```json
"No git state-modifying commands were executed without explicit authorization."
```

Replace with:
```json
"No git state-mutating commands (commit, stash, push, reset, rebase, merge, cherry-pick, clean, checkout, switch, branch -D) were executed without explicit per-command authorization; uncommitted work was treated as potentially belonging to parallel agents or developers."
```

**Step 5: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('.sdd/spec/mandates.json')); print('JSON valid')"
```

Expected: `JSON valid`

---

## Task 3: Add G023 to `guidelines.dsl`

**Files:**
- Modify: `.sdd/source/guidelines.dsl:250-251` (append after closing `}` of G022)

**Step 1: Open `.sdd/source/guidelines.dsl`** and go to line 250 (end of G022 block).

**Step 2: Append G023 after the closing `}` of G022:**

```
guideline G023 {
  type: SOFT
  title: "Git Safety Practices"
  description: "Operational guidance for git command safety under M010 parallel-state assumption. Before any mutating action: run git status/diff first. Prefer direct file edits over git workflow commands. Do not stash, commit, cherry-pick, or push automatically — provide a summary and suggested commit message instead. Treat uncommitted work as potentially belonging to parallel agents or developers. Before any restricted command, state what it does, why it is needed, what state it may affect, and whether safer alternatives exist."
  category: governance
  mandate_ref: M010
  examples: [
    "After completing work: provide summary + suggested commit message, do not run git commit -> OK",
    "Before git stash: explain impact on parallel work, wait for approval -> OK",
    "git stash pop without asking -> VIOLATION",
    "git commit after task completion without explicit user instruction -> VIOLATION",
    "git status to inspect state before proposing action -> OK"
  ]
}
```

**Step 3: Verify the file ends cleanly**

```bash
tail -20 .sdd/source/guidelines.dsl
```

Expected: G023 block visible, no syntax errors apparent.

---

## Task 4: Compile and regenerate governance artifacts

**Step 1: Run governance compile**

```bash
sdd governance compile
```

Expected: no errors. This regenerates derived artifacts from source files.

**Step 2: Run governance generate**

```bash
sdd governance generate
```

Expected: no errors. This regenerates `agent-instructions.md`, `CLAUDE.md`, fingerprints, and metadata.

**Step 3: Run governance validate**

```bash
sdd governance validate
```

Expected: passes. If it reports drift or errors, investigate before proceeding.

---

## Task 5: Verify derived artifacts

**Step 1: Check `metadata.json` fingerprint was updated**

```bash
python3 -c "import json; d=json.load(open('.sdd/metadata.json')); print('M010 fingerprint:', d['fingerprints']['mandates']['M010']); print('guidelines_count:', d.get('guidelines_count', 'field missing'))"
```

Expected: M010 fingerprint is different from `ef3c0076c1b0e55e` (prior value). Note whether `guidelines_count` was updated or is absent.

**Step 2: Check `agent-instructions.md` reflects M010**

```bash
grep -A5 "M010" .sdd/agent-instructions.md
```

Expected: M010 entry visible in the active mandates list.

**Step 3: Verify M010 in `mandates.md` is unchanged by compile/generate**

```bash
grep -A20 "## M010" .sdd/source/mandates/mandates.md
```

Expected: the shared state principle paragraph and the expanded violations list are still present (compile should not overwrite source files).

---

## Validation Checklist

Before considering this complete:

- [ ] `mandates.md` M010 section contains "Shared state assumption" paragraph
- [ ] `mandates.md` M010 violations list includes "git mutation without approval" with full command list
- [ ] `mandates.json` M010 `rationale` includes shared state principle
- [ ] `mandates.json` M010 `enforcement_steps[-1]` includes stash, cherry-pick, clean, checkout, switch, branch -D
- [ ] `mandates.json` M010 `validation[-1]` updated to match
- [ ] `guidelines.dsl` contains G023 block with `mandate_ref: M010`
- [ ] `sdd governance compile` passes
- [ ] `sdd governance generate` passes
- [ ] `sdd governance validate` passes
- [ ] `metadata.json` M010 fingerprint differs from `ef3c0076c1b0e55e`

---

## Notes

- Do NOT modify `governance-core.json` or `governance-client.json` directly — these are generated by `sdd governance compile`.
- Do NOT modify `agent-instructions.md` directly — it is regenerated by `sdd governance generate`.
- If `sdd governance compile` fails with a schema error on `mandates.json`, check that the JSON is valid and that no field names were changed.
- The `guidelines_count` field in `metadata.json` may not auto-increment for DSL guidelines (those are language-adapter guidelines); if it stays at 0 after generate, that is expected — note it but do not force-edit metadata.json.
