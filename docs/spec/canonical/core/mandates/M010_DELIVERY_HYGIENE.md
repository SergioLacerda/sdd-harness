# Mandate: Delivery Hygiene Enforcement

**ID:** M010
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** post-execution

---

## Objective

Guarantee that every implementation is delivered with updated tests and strict
quality hygiene, including mandatory auto-fix and revalidation before handoff.

Git state-modifying operations (commit, push, add, reset, etc.) are NEVER
executed autonomously — only the human controls the git state.

---

## Part A: Code Quality (MUST)

1. For any code change, the agent MUST create or update relevant tests.
2. If `ruff` is available, the agent MUST run `ruff check --fix .`.
3. If a formatter is configured, the agent MUST run the formatter
   (`ruff format .` or `black .`).
4. If `mypy` is detected, the agent MUST run `mypy .`.
5. If `pytest` is detected, the agent MUST run `pytest`.
6. The agent MUST re-run lint/type/tests after auto-fix and formatting.

---

## Part B: Git Autonomy Protocol (HARD — never violate)

**The agent MUST NEVER execute git state-modifying commands autonomously.**

State-modifying git commands include but are not limited to:
`git add`, `git commit`, `git push`, `git reset`, `git rebase`,
`git merge`, `git cherry-pick`, `git branch -D`, `git stash`.

### Rule: Suggest — Never Execute

When a commit would be appropriate, the agent MUST:

1. Prepare the complete, ready-to-run command block (staged files + commit message).
2. Present it to the human in a code block.
3. Stop and wait. Do NOT execute.

### Authorization Requirements

The ONLY valid authorization for git state-modifying commands is an **explicit,
unambiguous human instruction** in the current message. Examples:

| Phrase | Authorized? |
|--------|-------------|
| "commita", "commit isso", "faz o commit" | ✅ Yes |
| "push", "manda pro remote" | ✅ Yes |
| "aplicar", "aplicar soluções" | ❌ No — implements code, not git |
| "continuar", "seguir", "pronto", "ok" | ❌ No — completion, not git |
| "seguir com implementação" | ❌ No — implements, not git |
| tests passing / make check passing | ❌ No — quality gate, not git auth |
| task completion feeling | ❌ No — never infer git authorization |

### Pre-Bash Checklist (enforce before every Bash call)

Before invoking Bash, the agent MUST ask:
> "Does this command modify git state?"

If YES → present as a code block suggestion and STOP. Do not call Bash.
If NO → proceed.

**Read-only git commands (`git status`, `git log`, `git diff`) are allowed.**

---

## Validation Checklist

- [ ] Tests were added or updated for changed behavior.
- [ ] `ruff check --fix .` executed (when available).
- [ ] Formatter executed (when configured).
- [ ] `ruff check .` passes after fixes.
- [ ] `mypy .` passes when available.
- [ ] `pytest` passes when available.
- [ ] Final handoff includes PDQG evidence of command execution and re-run.
- [ ] No git state-modifying commands were executed without explicit authorization.

---

## Failure Mode

If any required step fails, delivery is `BLOCKED`.

- No tests added/updated for changed code => `BLOCKED`
- Auto-fix/format introduces unresolved errors => `BLOCKED`
- Revalidation fails (`ruff`, `mypy`, or `pytest`) => `BLOCKED`
- Git state-modifying command executed without explicit authorization => `VIOLATION`

---

## Rationale

`ruff check` alone verifies but does not remediate. Strict hygiene requires
auto-fix first, then full revalidation to prevent handing off avoidable style
and lint debt to human reviewers.

Git autonomy is prohibited because it bypasses human code review, creates
unintended commits, and breaks auditability. Task completion is NOT authorization
for committing — these are independent lifecycle events.
