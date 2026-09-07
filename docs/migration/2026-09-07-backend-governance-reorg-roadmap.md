# Backend Governance Reorganization Roadmap

> Roadmap. Produced by Strategist mission `20260907-backend-governance-reorg-refinement`
> (refined package: `.analysis/refined/20260907-backend-governance-reorg-refinement/`). This
> document reconciles `.analysis/pending/ACHADOS_E_MELHORIAS_PROVIDENTIA.md`'s P0→P3 roadmap
> and `.analysis/pending/nova_arquitetura.txt.txt`'s Fase 0→7 migration plan into one sequence.
> Landing-page work is explicitly excluded — already applied in parallel missions. This is a
> spec for future coding tasks; it does not itself change any file under `packages/`.

## Reconciled Phase Sequence

| Phase | Source label(s) | Status |
|---|---|---|
| Fase 0 — naming ADR | nova_arq Fase 0 | ✅ done (`ADR-023`) |
| *(landing identity)* | nova_arq Fase 7 (partial, ahead of sequence) | ✅ done, scoped exception — not full Fase 7 |
| **Fase 1 — extract Governed Intake** | nova_arq Fase 2 / ACHADOS P0 | **next action — detailed below** |
| Fase 2 — universalize Execution Contract | nova_arq Fase 3 / ACHADOS P1 | outline only |
| Fase 3 — separate capabilities | nova_arq Fase 4 / ACHADOS P1 (tail) | outline only |
| Fase 4 — Context Broker | nova_arq Fase 5 / ACHADOS P2 | outline only |
| Fase 5 — SDD as policy pack | nova_arq Fase 6 | outline only |
| Fase 6 — remaining backend rename | nova_arq Fase 7 (backend remainder) | outline only, decision-blocked |

## Hard Constraints (apply to every phase)

- No mechanical `ask_*` → `provident_*` rename at any point — classify each symbol by real
  responsibility before moving it.
- No LLM/provider call where a deterministic signal already resolves the decision.
- No new top-level package created preemptively — start as a subpackage inside the existing
  `sdd_runtime` package; promote to an independent package only on proven need.
- No public CLI command per capability — `--capability` is an advanced override, not the
  normal path.
- No promoting Evidence Cards (Fase 4) to a canonical source — they cache/reference the real
  source, never replace it.
- No adding a new architectural layer without a measured convergence/cost/maintenance gain.

## Fase 1 — Extract Governed Intake from `ask`

### Current state

`ask_response_intake.py` (`packages/interfaces/sdd_cli/src/sdd_cli/services/`, 166 lines)
already contains five functions matching the target extraction almost verbatim:

```
classify_ask_intent(query, skill) -> str
resolve_ask_entrypoint() -> tuple[str, str | None]
resolve_ask_next_action(execution_gate, intent) -> str
resolve_execution_gate(*, organize_used, organize_reason) -> str
build_intake_contract_fields(*, execution_gate, query, skill) -> dict[str, Any]
```

`build_intake_contract_fields` calls the first two internally and returns the additive
intake-contract dict consumed by `emit_ask_intake_only_json_response`. `ask_entry.py`'s Typer
callback carries no intake logic — it validates/normalizes the query and delegates immediately
to `_ask_backend.ask_cmd(...)`.

Separately, `AskHandler.pre_run()` (`packages/core/sdd_runtime/src/sdd_runtime/
_skill_executor/_handlers/_ask.py`) calls a **different** function,
`_build_execution_contract(context)` (in `_context_builders.py`), producing a
differently-shaped `execution_contract` dict (`historical_context`, `task_type`, `goal`).
**This duplication is live evidence that the execution contract isn't a universal currency
yet.** Fase 1 does not attempt to unify these two — that's Fase 2's job. Fase 1 only relocates
the five intake functions and documents the duplication as Fase 2's trigger.

### Target structure

Per the "no new top-level package" constraint, inside the existing `sdd_runtime` package:

```
packages/core/sdd_runtime/src/sdd_runtime/intake/
├── __init__.py
├── intent.py            # classify_ask_intent, _looks_like_implementation_intent
├── entrypoint.py         # resolve_ask_entrypoint, ASK_ENTRYPOINT_ENV
├── gate.py                # resolve_execution_gate
├── routing.py              # resolve_ask_next_action
└── contract_builder.py      # build_intake_contract_fields
```

### Migration approach — additive move + re-export shim, not a big-bang cut

`ADR-012` exists precisely because a prior attempt to move `_ask_backend.py` logic broke ~121
`unittest.mock.patch` call sites across 9 test files that patched symbols at their old module
path. Fase 1 must not repeat that: `ask_response_intake.py` keeps its five function names as
**thin re-exports** of the relocated implementations — existing callers and existing test
`mock.patch` targets keep working unmodified. This is a deliberate, temporary compatibility
seam; removing it is a later, separately-decided deprecation step.

### Acceptance criteria for Fase 1

- `sdd_runtime/intake/` subpackage exists with the five functions, no behavior change.
- `ask_response_intake.py`'s five function names still exist and behave identically (thin
  re-exports) — every existing caller and test keeps working unmodified.
- New unit tests for the relocated functions live alongside the new module.
- `ask_entry.py` → `_ask_backend.ask_cmd(...)` flow is unaffected.
- `AskHandler`/`_build_execution_contract` are **not** touched in this phase.
- `make pre-delivery` (or the project's existing test/lint gate) passes.
- Opportunity Attack candidate: this phase may warrant its own ADR once implemented — flagged
  for whoever executes Fase 1 to evaluate, not decided here.

## Fases 2–6 — Outline Only

Each becomes its own refinement mission when its turn comes.

### Fase 2 — Universalize the Execution Contract

**Goal:** one versioned `ExecutionContract` schema; Fase 1's intake-contract fields and
`_build_execution_contract`'s fields merge into it. `AskHandler` stops owning contract
construction — Governed Intake produces the contract, capabilities receive it, skills may
append results but never elevate their own authority fields (scope/risk/approval).

**Acceptance criteria:** schema is versioned (`schema_version`) and validated at every
boundary; a capability cannot widen its own scope or risk; the contract's origin is traceable.

### Fase 3 — Separate Capabilities

**Goal:** formalize Capability ≠ Skill ≠ Pipeline. Capability IDs (`query`, `diagnose`,
`correct`, `converge`, `organize`, `review_architecture`) become the routing currency; the
router stops depending on concrete skill names.

**Acceptance criteria:** router selects by capability ID + declared risk/input-contract, not
`if skill.name == "..."` conditionals; a capability's implementation can change without
touching routing code.

### Fase 4 — Context Broker

**Goal:** evolve the existing `ContextLoader` into a broker (Source Registry, Retrieval
Planner, Trust/Freshness Scorer, Deduplicator, layered compression L0→L1→L2, Evidence Store,
Budget Controller).

**Acceptance criteria:** `ContextLoader.load(...)`'s existing call sites keep working;
compression failure becomes an observable, structured result instead of a debug-only log line;
Evidence Cards are cacheable/traceable but never substitute the canonical source.

### Fase 5 — SDD as a Policy Pack

**Goal:** introduce a `GovernancePolicyPack` protocol (`match`, `evaluate`, `context_sources`,
`validations`); move SDD-specific mandates/routing/validation behind it; the kernel stops
importing SDD-specific types directly.

**Acceptance criteria:** architectural decoupling only — no requirement to ship a second
policy pack; the kernel just needs to no longer structurally require SDD-specific imports.

### Fase 6 — Remaining Backend Rename

**Goal:** whatever backend-facing renaming (CLI binary, package names, repository name)
remains after Fases 1–5.

**Status:** explicitly **not authorized** by `ADR-023` yet. Cannot be meaningfully scoped
until a separate, explicit decision authorizes it — listed for sequence completeness only.

## Out of scope for this document

No code change. Fase 1's implementation (`sdd_runtime/intake/` subpackage + shims) is a
separate coding task, tracked as `implementation_handoff` in the Strategist mission's
`tasks.md`. Fases 2–6 are not scoped to file level here — each awaits its own refinement
mission.
