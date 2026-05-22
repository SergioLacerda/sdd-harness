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

**Last Updated:** 2026-05-19
**Authority:** SDD Harness v0.1.0+
**Scope:** Runtime implementation decisions only
