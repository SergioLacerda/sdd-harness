# 🗺️ Canonical Specification Map (LLM Semantic Entrypoint)

> **Context:** This is the root of the SDD Canonical Specification. Use this map to navigate deep technical and governance rules.
> **Navigation:** For AI agents, see the [Semantic Map](./SEMANTIC_MAP.md) for deep knowledge graph navigation.

## 🏗️ Core (Immutable Governance Kernel)
*Non-negotiable rules and mandates that govern all agent behavior.*

- **Mandates**: [core/meta/mandate.spec](./core/meta/mandate.spec) — The 3 primary execution mandates (M001-M003).
- **Guidelines**: [core/meta/guidelines.dsl](./core/meta/guidelines.dsl) — Customization rules for the governance system.
- **Policies**: [core/policies/index.md](./core/policies/index.md) — Enforcement levels (Strict/Permissive).
- **Invariants**: [core/INDEX.md](./core/INDEX.md) — Architectural lock-in rules.

## 🧩 Specifications (Technical Guardrails)
*Technical standards for implementing features and maintaining code quality.*

- **Definition of Done**: [specifications/definition_of_done.md](./specifications/definition_of_done.md) — 45+ criteria for task completion.
- **Security Model**: [specifications/security-model.md](./specifications/security-model.md) — Rules for subprocesses, shell execution, and path validation.
- **Testing Standard**: [specifications/testing.md](./specifications/testing.md) — TDD requirements and layer coverage.
- **Architecture**: [specifications/architecture.md](./specifications/architecture.md) — Ports & Adapters (Hexagonal) alignment.

## 🚀 Key Features
*Specific framework capabilities and their governing rules.*

- **Clean Architecture**: [features/CLEAN_ARCHITECTURE.md](./features/CLEAN_ARCHITECTURE.md)
- **TDD Workflow**: [features/TDD.md](./features/TDD.md)
- **Customization**: [features/CUSTOMIZATION_GOVERNANCE.md](./features/CUSTOMIZATION_GOVERNANCE.md)

---
**Note for Agents:** All mandates are strictly enforced via SHA-256 fingerprints compiled into the `.sdd/` control plane. Any modification to `core/meta/` requires running `sdd governance validate` to refresh the session signature.
