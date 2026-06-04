# Architecture Decision Records — SDD Harness Runtime

Local ADRs specific to the SDD Harness runtime layer. These are distinct from `docs/spec/decisions/` which contains framework-level ADRs.

---

## 📋 Harness-Local ADRs

### ADR-001: Runtime Authority Boundary (2026-05-10)

**Decision:** Define the authority boundary between governance specifications and runtime implementation.

**Rationale:**

- Governance specs (`docs/spec/canonical/`) are the source of truth
- Compiled artifacts are immutable snapshots
- Runtime execution engine (`sdd_runtime`) is a pure executor, not a normative authority
- Prevents runtime from overriding specs

**Links:**

- [ADR-001-runtime-authority-boundary.md](ADR-001-runtime-authority-boundary.md)
- Implements M003 (Context Awareness), M005 (Token Economy)
- Enforced by `GovernanceOrchestrator` in `sdd_core`

---

### ADR-002: Intelligence Provider Architecture (2026-05-11)

**Decision:** Implement pluggable intelligence providers for context compression and analysis.

**Rationale:**

- Single if/else solution doesn't scale (new providers always needed)
- Factory pattern too rigid for runtime swapping
- ABC/Protocol allows runtime discovery and fallback chain
- `ProviderRegistry` enables cascading: HTTP → AST → TFIDF → LocalProvider

**Providers:**

- `HttpProvider` — External intelligence service (if configured)
- `AstProvider` — Abstract syntax tree analysis
- `TfidfProvider` — Statistical text frequency analysis
- `LocalIntelligenceProvider` — Fallback (always available)

**Links:**

- [ADR-002-intelligence-provider-architecture.md](ADR-002-intelligence-provider-architecture.md)
- Implements M005 (Token Economy) compression obligations
- Implementation: `sdd_runtime` package, `intelligence_providers.py`

---

### ADR-003: Skill Handler Strategy Pattern (2026-05-19)

**Decision:** Replace `if skill.name == "sdd-ask"` chains in `run_skill` with per-skill handler classes (`AskHandler`, `CorrectHandler`, etc.) discovered via name convention.

**Rationale:**

- `run_skill` had cyclomatic complexity of 12 (`# noqa: C901`)
- Every new skill with lifecycle hooks required editing `run_skill` in 2–3 places
- Strategy pattern: adding a new skill = new handler class, zero changes to `run_skill`

**Links:**

- [ADR-003-skill-handler-strategy-pattern.md](ADR-003-skill-handler-strategy-pattern.md)
- Implementation: `_skill_executor.py` (handlers + `_get_skill_handler` factory)

---

### ADR-004: SkillEngine Split into SkillRegistry + SkillExecutor (2026-05-19)

**Decision:** Split the 414-line `SkillEngine` into `SkillRegistry` (disk loading, lookup, export) + `SkillExecutor` (run_skill, commands, telemetry) + `SkillEngine` thin facade.

**Rationale:**

- Registry and execution have different change reasons and different collaborators
- Each class independently testable without the full engine
- Zero breaking changes: all callers continue to use `SkillEngine`

**Links:**

- [ADR-004-skillengine-registry-executor-split.md](ADR-004-skillengine-registry-executor-split.md)
- Files: `_skill_registry.py`, `_skill_executor.py`, `skills.py`

---

### ADR-005: `_REGISTRY` Stays in `skills.py` (2026-05-19)

**Decision:** Keep the hardcoded `_REGISTRY` dict in `skills.py` and pass it to `SkillRegistry` as a constructor parameter, preserving a live reference for test mutation support.

**Rationale:**

- Moving `_REGISTRY` to `_skill_registry.py` is semantically clean but architecturally unnecessary
- `SkillRegistry(fallback, project_root)` is generic and testable with any dict
- Live reference (`self._fallback`) allows post-construction mutations to remain visible via `get_skill`

**Links:**

- [ADR-005-registry-fallback-in-skills-facade.md](ADR-005-registry-fallback-in-skills-facade.md)

---

### ADR-006: CLI Canonical JSON Envelope — Big-Bang Cut (2026-05-21)

**Decision:** All CLI JSON responses use a single canonical envelope `{status, command, ok, error, data}`. Legacy mirroring and `SDD_CLI_ENVELOPE_STRICT` removed atomically.

**Rationale:**

- Dual-payload pattern required maintaining two code paths indefinitely
- Feature flag had no planned graduation date
- Big-bang cut guarantees the codebase is never in an ambiguous state post-merge

**Links:**

- [ADR-006-cli-canonical-json-envelope.md](ADR-006-cli-canonical-json-envelope.md)
- Implementation: `packages/interfaces/sdd_cli/src/sdd_cli/shared/contracts.py`

---

### ADR-007: Environment Variable Precedence Matrix (2026-05-21)

**Decision:** A single explicit matrix governs all path-resolution env vars, with R/O/F classification per environment (`test`, `runtime`, `dev/prod`).

**Rationale:**

- Per-module ad-hoc resolution caused silent cross-test contamination and non-reproducible CI behaviour
- Single contract is predictable, testable, and auditable

**Links:**

- [ADR-007-environment-variable-precedence-matrix.md](ADR-007-environment-variable-precedence-matrix.md)

---

### ADR-008: `trace_id` Propagation as Explicit Function Argument (2026-05-21)

**Decision:** `trace_id` travels as an explicit argument through the call chain. No thread-locals, no globals.

**Rationale:**

- Thread-locals and context vars create invisible coupling and break in async contexts
- Explicit argument makes propagation visible in signatures and testable in isolation

**Links:**

- [ADR-008-trace-id-as-explicit-argument.md](ADR-008-trace-id-as-explicit-argument.md)
- Related: M007 (Telemetry Enforcement)

---

### ADR-009: Progressive Enforcement Ladder (WARN → BLOCK → STRICT) (2026-05-21)

**Decision:** Governance enforcement uses a three-phase ladder; rules advance based on measured stability, not calendar.

**Rationale:**

- Binary enforce/skip creates incentive to delay activation indefinitely
- Evidence-based promotion prevents rules from becoming permanent advisory signals

**Links:**

- [ADR-009-progressive-enforcement-ladder.md](ADR-009-progressive-enforcement-ladder.md)
- [ADR-009-threshold-signoff.md](ADR-009-threshold-signoff.md)
- Related: M010 (Governance Hardening)

---

### ADR-010: structlog as the Logging Primitive (2026-05-21)

**Decision:** `structlog` replaces raw `print()` across all 6 packages. A single `sdd_core/logging.py` module is the only place structlog is configured. ConsoleRenderer for dev/TTY, JSONRenderer for production/non-TTY.

**Rationale:**

- stdlib logging requires more complex configuration for structured output
- Single config module prevents renderer drift and ensures processor chain consistency

**Links:**

- [ADR-010-structlog-as-logging-primitive.md](ADR-010-structlog-as-logging-primitive.md)
- Implementation: `packages/core/sdd_core/src/sdd_core/logging.py`

---

### ADR-011: Golden Snapshot Drift Classification (2026-05-21)

**Decision:** Drift is classified as Type A (volatile-only), B (backward-compat), or C (breaking). Each type has a defined evidence requirement and review path.

**Rationale:**

- Ad-hoc refresh produced no audit trail; regressions accepted silently
- Typed classification scales review burden to actual risk of the change

**Links:**

- [ADR-011-golden-snapshot-drift-classification.md](ADR-011-golden-snapshot-drift-classification.md)

## 🧾 Operational Appendices

These artifacts support governance operations but are not ADRs:

- [Threshold signoff: progressive-enforcement-ladder](ADR-009-threshold-signoff.md)

---

## 📚 Related

- **Framework ADRs:** [docs/spec/decisions/](../spec/decisions/) — ADR-001 through ADR-010
- **Authority Hierarchy:** [docs/spec/canonical/core/INDEX.md](../spec/canonical/core/INDEX.md) — CORE is immutable kernel
- **Runtime Layer:** [docs/runtime/protocols/AGENT_ENTRYPOINT.md](../runtime/protocols/AGENT_ENTRYPOINT.md) — Bootstrap protocol

---

## 🔄 Adding New Harness ADRs

When adding a new runtime ADR:

1. **Filename:** `ADR-NNN-title-slug.md`
2. **Format:** Use standard ADR format (Decision, Rationale, Impact, Alternatives, Links)
3. **Authority:** If conflicts with governance specs → governance specs win
4. **Testing:** Include test file references if applicable
5. **Review:** Require SDD core team review before merge

---

**Last Updated:** 2026-05-24
**Authority:** SDD Harness v0.1.0+
**Scope:** Runtime implementation decisions only
