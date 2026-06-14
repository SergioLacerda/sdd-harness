"""Template for .sdd/agent-instructions.md."""

from __future__ import annotations


def build_agent_instructions(
    spec_fingerprint: str,
    generated_at: str,
    mandates_list: str,
) -> str:
    """Render .sdd/agent-instructions.md content."""
    return f"""# SDD Agent Instructions — Authority & Bootstrap

**This workspace is governed by Spec Driven Development (SDD).**

You MUST NOT proceed without reading this file in its entirety.

---

## 1. Authority Hierarchy

**The source of truth for all governance is this directory (`.sdd/`).**

```
.sdd/
├── metadata.json                      ← Workspace version + fingerprints
├── agent-instructions.md              ← THIS FILE (you are reading it)
├── compiled/                          ← Optional binary/runtime artifacts (may be absent in template handoff)
└── source/
    ├── mandates/mandates.md           ← Mandate descriptions (enforcement rules)
    └── README.md
```

**Do not trust CLAUDE.md, .vscode/, .cursor/, or any other "convenience" pointers over what is in `.sdd/`.**

---

## 2. Mandatory Bootstrap (3 steps)

Before planning, coding, or deciding:

1. **Read `.sdd/metadata.json`**
   - Check `version` (currently 3.0)
   - Check `mandates_count` (count of active mandates)
   - Verify workspace is not stale
   - Expected fingerprint prefix (first 8 chars): {spec_fingerprint}

2. **Read `.sdd/metadata.json`**
   - Extract mandate IDs and titles
   - Example: `"items": [{{"id": "M001", "title": "Clean Architecture"}}, ...]`
   - If `items` is empty or count < 4, governance is broken → escalate to human

3. **Read `.sdd/source/mandates/mandates.md`**
   - Understand enforcement rules for each active mandate
   - If descriptions are stale or missing, request governance regeneration from the human

---

## 3. Active Mandates (read from `.sdd/source/`)

The authoritative human-readable list is in `.sdd/metadata.json`, not this file.

**Current snapshot** (validate this against `.sdd/metadata.json`):
{mandates_list}

---

## 4. Pre-Task Checklist

Before starting any work:

- [ ] `.sdd/metadata.json` read → version, fingerprint, count verified
- [ ] `.sdd/metadata.json` read → mandates extracted
- [ ] `.sdd/source/mandates/mandates.md` read → enforcement rules understood
- [ ] No contradictions between this file and `.sdd/` (if found → escalate)

**If you cannot complete this checklist, do not proceed — ask the human first.**

---

## 5. Enforcement Scope

Mandates (HARD) are non-negotiable and always take precedence.

Policies, rules, and guidelines (SOFT) must also be applied when they do not conflict with mandates.

Git protocol (M010), testing, architecture, and token budgets must be followed.

### HARD Constraints — Never Violate

These constraints are non-negotiable. Violation requires human escalation, not auto-correction.

- **M010 (Delivery Hygiene)**: NEVER execute git state-modifying commands (add, commit, push, reset, merge, rebase, branch -D, etc.) autonomously via any tool or shell. ONLY suggest git commands in ready-to-run blocks for human execution.
  - Corollary: Task completion does NOT authorize a commit. Only explicit user request does.
  - Read: `.sdd/source/mandates/mandates.md#M010`

---

## Governance Mode

When operating under SDD via a skill or CLI entry point (`sdd ask`, `sdd-ask`, `sdd-converge`, etc.),
the execution context is **HARD governance mode**.

| Entry point | Mode |
|-------------|------|
| `sdd ask` / `sdd-ask` skill | HARD |
| `sdd-converge`, `sdd-correct`, `sdd-stabilize` | HARD |
| Direct API / notebook / ad-hoc | SOFT |

### HARD Mode Rules

**Rule 1 — Execution gate:**
If `sdd ask` output contains `execution_gate: blocked`, **STOP immediately**.
Report the `gate_reason` to the user. Do not proceed with any action until the user re-authorizes.

**Rule 2 — Git authorization:**
Git state-modifying commands (`add`, `commit`, `push`, `reset`, `merge`, `rebase`, etc.)
are **blocked** unless the current user message contains explicit authorization.
Task completion is NOT authorization. "Fix the tests" is NOT authorization. Only explicit phrases
like "commit this", "push to remote", "run git add and commit" constitute authorization.

**Rule 3 — `intake_index_mode: none` is an independent signal, not "the gate":**
`intake_index_mode: none` means no governance context was indexed for this query.
This is **separate from Rule 1** — `execution_gate` may be `allowed` while
`intake_index_mode` is still `none` (e.g. for short queries). This is a **signal to
surface to the user and stop** — not a green light to proceed, and not the same as
"the gate is blocked". Report both fields by name/value and wait for the user to
decide how to continue.

---

## 6. Fallback & Escalation

**If `.sdd/` is incomplete or inconsistent:**
- **STOP EXECUTION IMMEDIATELY. Do not guess or interpolate.**
- Escalate to human: "`.sdd/` is broken: [specific problem]"
- Example: "`.sdd/metadata.json` has only 1 mandate but `.sdd/metadata.json` claims 4"
- You must refuse to bypass the governance gate.

**This is not a blocker — it's a signal that the human should regenerate the workspace.**

---

## 7. Fingerprint Integrity Check

**Fingerprint this version:** `{spec_fingerprint}`
**Generated at:** {generated_at}

Before starting any task, verify bootstrap integrity:

1. Read the fingerprint in your bootstrap file header (e.g. `# Governance fingerprint:` in CLAUDE.md)
2. Compare with `.sdd/metadata.json` → field `governance_fingerprint`
3. If they differ, governance was updated after bootstrap. Run `sdd governance generate` to sync.

If `sdd governance generate` does not update `.sdd/agent-instructions.md`, ask the human to run `sdd wizard` again.

**Golden rule:** Fingerprint in bootstrap file = fingerprint in metadata.json. Divergence = drift.
"""
