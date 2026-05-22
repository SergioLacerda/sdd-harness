# 🧭 NAVIGATION — Find Documentation by Task

**Use this to search for specific topics without reading everything.**

Search your task in the table below → follows links to exactly what you need.

---

## 🔍 Quick Search

### By Task Type

| Task | Find Here |
|------|-----------|
| **I'm new, where do I start?** | [_START_HERE.md](./_START_HERE.md) |
| **I'm implementing a feature** | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md) → PHASE 5 |
| **I need to understand rules** | [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) (16 rules) |
| **I'm debugging test failure** | [testing.md](./docs/ia/CANONICAL/specifications/testing.md) + [emergency/TEST_FAILURE.md](./docs/ia/guides/emergency/TEST_FAILURE_GUIDE.md) |
| **Code won't pass import checker** | [ADR-003-ports-adapters.md](./docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md) |
| **Commit hook is blocking me** | [emergency/PRE_COMMIT_HOOK_FAILURE.md](./docs/ia/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md) |
| **I need to name something** | [conventions.md](./docs/ia/CANONICAL/rules/conventions.md) |
| **I'm confused about architecture** | [architecture.md](./docs/ia/CANONICAL/specifications/architecture.md) |
| **I have questions** | [FAQ.md](./docs/ia/guides/reference/FAQ.md) |
| **I don't know terminology** | [GLOSSARY.md](./docs/ia/guides/reference/GLOSSARY.md) |

---

### By Layer

#### 🔴 Constitutional (Immutable)
- [constitution.md](./docs/ia/CANONICAL/rules/constitution.md) — 15 principles, never changes

#### 🟠 Rules (Mandatory)
- [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) — 16 mandatory rules
- [conventions.md](./docs/ia/CANONICAL/rules/conventions.md) — Naming, structure, patterns

#### 🟡 Architecture (Decisions)
- [ADR-001-autonomous-agents.md](./docs/ia/CANONICAL/decisions/ADR-001-autonomous-agents.md)
- [ADR-002-three-layer-architecture.md](./docs/ia/CANONICAL/decisions/ADR-002-three-layer-architecture.md)
- [ADR-003-ports-adapters-pattern.md](./docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md)
- [ADR-004-isolated-testing.md](./docs/ia/CANONICAL/decisions/ADR-004-isolated-testing.md)
- [ADR-005-thread-isolation.md](./docs/ia/CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md)
- [ADR-006-governance-automation.md](./docs/ia/CANONICAL/decisions/ADR-006-governance-automation.md)

#### 🟢 Specifications (How To)
- [architecture.md](./docs/ia/CANONICAL/specifications/architecture.md) — Overall structure
- [testing.md](./docs/ia/CANONICAL/specifications/testing.md) — Test patterns
- [feature-checklist.md](./docs/ia/CANONICAL/specifications/feature-checklist.md) — Quality gate
- [definition-of-done.md](./docs/ia/CANONICAL/specifications/definition-of-done.md) — 45+ criteria
- [communication.md](./docs/ia/CANONICAL/specifications/communication.md) — Docs + clarity

#### 🔵 Guides (Operational)
- [PHASE-0-AGENT-ONBOARDING.md](./docs/ia/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md) — First setup
- [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md) — 7-phase workflow
- [DEVELOPMENT_WORKFLOW_VALIDATION.md](./docs/ia/guides/operational/DEVELOPMENT_WORKFLOW_VALIDATION.md)
- [METRICS_TRACKING.md](./docs/ia/guides/operational/METRICS_TRACKING.md)
- [PRE_COMMIT_HOOKS.md](./docs/ia/guides/operational/PRE_COMMIT_HOOKS.md)

#### 🟣 Emergency (Crisis)
- [README.md](./docs/ia/guides/emergency/README.md) — Pick your emergency
- [PRE_COMMIT_HOOK_FAILURE.md](./docs/ia/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md)
- [TEST_FAILURE_GUIDE.md](./docs/ia/guides/emergency/TEST_FAILURE_GUIDE.md)
- [RULES_VIOLATION_DETECTED.md](./docs/ia/guides/emergency/RULES_VIOLATION_DETECTED.md)
- [IMPORTS_CORRUPTED.md](./docs/ia/guides/emergency/IMPORTS_CORRUPTED.md)
- [METRICS_CORRUPTION_RECOVERY.md](./docs/ia/guides/emergency/METRICS_CORRUPTION_RECOVERY.md)

#### ⚫ Reference (Questions)
- [FAQ.md](./docs/ia/guides/reference/FAQ.md) — Common questions
- [GLOSSARY.md](./docs/ia/guides/reference/GLOSSARY.md) — Term definitions
- [HOW_EACH_LAYER_WORKS.md](./docs/ia/guides/reference/HOW_EACH_LAYER_WORKS.md) — Deep dives

---

### By Role

#### 👨‍💻 Individual Contributor
Start → [_START_HERE.md](./_START_HERE.md)
Implement → [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md)
Rules → [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md)

#### 🧑‍🔬 Architect / Tech Lead
Read → [ADR-*.md](./docs/ia/CANONICAL/decisions/) (all decisions)
Validate → [DEVELOPMENT_WORKFLOW_VALIDATION.md](./docs/ia/guides/operational/DEVELOPMENT_WORKFLOW_VALIDATION.md)
Metrics → [METRICS_TRACKING.md](./docs/ia/guides/operational/METRICS_TRACKING.md)

#### 🤖 AI / Automation Agent
Setup → [PHASE-0-AGENT-ONBOARDING.md](./docs/ia/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)
Workflow → [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md)
Rules → [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) (must pass ≥80%)
Emergency → [Emergency Procedures](./docs/ia/guides/emergency/)

#### 🏢 DevOps / SRE
Setup → Pre-commit hooks: [PRE_COMMIT_HOOKS.md](./docs/ia/guides/operational/PRE_COMMIT_HOOKS.md)
Emergency → [PRE_COMMIT_HOOK_FAILURE.md](./docs/ia/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md)
Metrics → [METRICS_TRACKING.md](./docs/ia/guides/operational/METRICS_TRACKING.md)

---

### By Problem

| Problem | Solution |
|---------|----------|
| Tests failing | [TEST_FAILURE_GUIDE.md](./docs/ia/guides/emergency/TEST_FAILURE_GUIDE.md) |
| Commit blocked | [PRE_COMMIT_HOOK_FAILURE.md](./docs/ia/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md) |
| Rules violation | [RULES_VIOLATION_DETECTED.md](./docs/ia/guides/emergency/RULES_VIOLATION_DETECTED.md) |
| Imports broken | [IMPORTS_CORRUPTED.md](./docs/ia/guides/emergency/IMPORTS_CORRUPTED.md) |
| Metrics wrong | [METRICS_CORRUPTION_RECOVERY.md](./docs/ia/guides/emergency/METRICS_CORRUPTION_RECOVERY.md) |
| Don't understand | [FAQ.md](./docs/ia/guides/reference/FAQ.md) or [GLOSSARY.md](./docs/ia/guides/reference/GLOSSARY.md) |
| Can't find doc | (You are here! Try keywords below) |

---

## 🔑 Keywords Reference

**Looking for docs about these topics?**

- **Testing:** [testing.md](./docs/ia/CANONICAL/specifications/testing.md), [TEST_FAILURE_GUIDE.md](./docs/ia/guides/emergency/TEST_FAILURE_GUIDE.md)
- **Architecture:** [architecture.md](./docs/ia/CANONICAL/specifications/architecture.md), [ADR-*.md](./docs/ia/CANONICAL/decisions/)
- **Ports & Adapters:** [ADR-003-ports-adapters-pattern.md](./docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md)
- **Naming:** [conventions.md](./docs/ia/CANONICAL/rules/conventions.md)
- **Threading:** [ADR-005-thread-isolation-mandatory.md](./docs/ia/CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md)
- **Import Rules:** [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) (Rule #5)
- **Documentation:** [communication.md](./docs/ia/CANONICAL/specifications/communication.md)
- **Quality Gate:** [definition-of-done.md](./docs/ia/CANONICAL/specifications/definition-of-done.md)
- **First Time:** [PHASE-0-AGENT-ONBOARDING.md](./docs/ia/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)
- **Now Implement:** [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md)

---

## 🧭 Still Can't Find It?

1. Check [FAQ.md](./docs/ia/guides/reference/FAQ.md) (most common Qs)
2. Search INDEX.md in specific layer (e.g., `CANONICAL/INDEX.md`)
3. Check [GLOSSARY.md](./docs/ia/guides/reference/GLOSSARY.md) for terminology
4. Ask team in project Slack

---

**This page:** Navigation aid
**Use it:** Whenever you need to find something specific
**Updated:** April 19, 2026
