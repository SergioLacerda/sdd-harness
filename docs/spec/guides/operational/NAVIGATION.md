# 🧭 NAVIGATION — Find Documentation by Task

**Use this to search for specific topics without reading everything.**

Search your task in the table below → follows links to exactly what you need.

---

## 🔍 Quick Search

### By Task Type

| Task | Find Here |
|------|-----------|
| **I'm new, where do I start?** | [CORE__START_HERE.md](./CORE__START_HERE.md) |
| **I'm implementing a feature** | [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md) → PHASE 5 |
| **I need to understand rules** | [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) (16 rules) |
| **I'm debugging test failure** | [testing.md](.docs/spec/canonical/specifications/testing.md) + [emergency/TEST_FAILURE.md](.docs/spec/guides/emergency/TEST_FAILURE_GUIDE.md) |
| **Code won't pass import checker** | [ADR-003-ports-adapters.md](.docs/spec/canonical/decisions/ADR-003-ports-adapters-pattern.md) |
| **Commit hook is blocking me** | [emergency/PRE_COMMIT_HOOK_FAILURE.md](.docs/spec/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md) |
| **I need to name something** | [conventions.md](.docs/spec/canonical/rules/conventions.md) |
| **I'm confused about architecture** | [architecture.md](.docs/spec/canonical/specifications/architecture.md) |
| **I have questions** | [FAQ.md](.docs/spec/guides/reference/FAQ.md) |
| **I don't know terminology** | [GLOSSARY.md](.docs/spec/guides/reference/GLOSSARY.md) |

---

### By Layer

#### 🔴 Constitutional (Immutable)

- [constitution.md](.docs/spec/canonical/rules/constitution.md) — 15 principles, never changes

#### 🟠 Rules (Mandatory)

- [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) — 16 mandatory rules
- [conventions.md](.docs/spec/canonical/rules/conventions.md) — Naming, structure, patterns

#### 🟡 Architecture (Decisions)

- [ADR-001-autonomous-agents.md](.docs/spec/canonical/decisions/ADR-001-autonomous-agents.md)
- [ADR-002-three-layer-architecture.md](.docs/spec/canonical/decisions/ADR-002-three-layer-architecture.md)
- [ADR-003-ports-adapters-pattern.md](.docs/spec/canonical/decisions/ADR-003-ports-adapters-pattern.md)
- [ADR-004-isolated-testing.md](.docs/spec/canonical/decisions/ADR-004-isolated-testing.md)
- [ADR-005-thread-isolation.md](.docs/spec/canonical/decisions/ADR-005-thread-isolation-mandatory.md)
- [ADR-006-governance-automation.md](.docs/spec/canonical/decisions/ADR-006-governance-automation.md)

#### 🟢 Specifications (How To)

- [architecture.md](.docs/spec/canonical/specifications/architecture.md) — Overall structure
- [testing.md](.docs/spec/canonical/specifications/testing.md) — Test patterns
- [feature-checklist.md](.docs/spec/canonical/specifications/feature-checklist.md) — Quality gate
- [definition-of-done.md](.docs/spec/canonical/specifications/definition-of-done.md) — 45+ criteria
- [communication.md](.docs/spec/canonical/specifications/communication.md) — Docs + clarity

#### 🔵 Guides (Operational)

- [PHASE-0-AGENT-ONBOARDING.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md) — First setup
- [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md) — 7-phase workflow
- [DEVELOPMENT_WORKFLOW_VALIDATION.md](.docs/spec/guides/operational/DEVELOPMENT_WORKFLOW_VALIDATION.md)
- [METRICS_TRACKING.md](.docs/spec/guides/operational/METRICS_TRACKING.md)
- [PRE_COMMIT_HOOKS.md](.docs/spec/guides/operational/PRE_COMMIT_HOOKS.md)

#### 🟣 Emergency (Crisis)

- [README.md](.docs/spec/guides/emergency/README.md) — Pick your emergency
- [PRE_COMMIT_HOOK_FAILURE.md](.docs/spec/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md)
- [TEST_FAILURE_GUIDE.md](.docs/spec/guides/emergency/TEST_FAILURE_GUIDE.md)
- [RULES_VIOLATION_DETECTED.md](.docs/spec/guides/emergency/RULES_VIOLATION_DETECTED.md)
- [IMPORTS_CORRUPTED.md](.docs/spec/guides/emergency/IMPORTS_CORRUPTED.md)
- [METRICS_CORRUPTION_RECOVERY.md](.docs/spec/guides/emergency/METRICS_CORRUPTION_RECOVERY.md)

#### ⚫ Reference (Questions)

- [FAQ.md](.docs/spec/guides/reference/FAQ.md) — Common questions
- [GLOSSARY.md](.docs/spec/guides/reference/GLOSSARY.md) — Term definitions
- [HOW_EACH_LAYER_WORKS.md](.docs/spec/guides/reference/HOW_EACH_LAYER_WORKS.md) — Deep dives

---

### By Role

#### 👨‍💻 Individual Contributor

Start → [CORE__START_HERE.md](./CORE__START_HERE.md)
Implement → [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)
Rules → [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md)

#### 🧑‍🔬 Architect / Tech Lead

Read → [ADR-*.md](.docs/spec/canonical/decisions/) (all decisions)
Validate → [DEVELOPMENT_WORKFLOW_VALIDATION.md](.docs/spec/guides/operational/DEVELOPMENT_WORKFLOW_VALIDATION.md)
Metrics → [METRICS_TRACKING.md](.docs/spec/guides/operational/METRICS_TRACKING.md)

#### 🤖 AI / Automation Agent

Setup → [PHASE-0-AGENT-ONBOARDING.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)
Workflow → [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)
Rules → [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) (must pass ≥80%)
Emergency → [Emergency Procedures](.docs/spec/guides/emergency/)

#### 🏢 DevOps / SRE

Setup → Pre-commit hooks: [PRE_COMMIT_HOOKS.md](.docs/spec/guides/operational/PRE_COMMIT_HOOKS.md)
Emergency → [PRE_COMMIT_HOOK_FAILURE.md](.docs/spec/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md)
Metrics → [METRICS_TRACKING.md](.docs/spec/guides/operational/METRICS_TRACKING.md)

---

### By Problem

| Problem | Solution |
|---------|----------|
| Tests failing | [TEST_FAILURE_GUIDE.md](.docs/spec/guides/emergency/TEST_FAILURE_GUIDE.md) |
| Commit blocked | [PRE_COMMIT_HOOK_FAILURE.md](.docs/spec/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md) |
| Rules violation | [RULES_VIOLATION_DETECTED.md](.docs/spec/guides/emergency/RULES_VIOLATION_DETECTED.md) |
| Imports broken | [IMPORTS_CORRUPTED.md](.docs/spec/guides/emergency/IMPORTS_CORRUPTED.md) |
| Metrics wrong | [METRICS_CORRUPTION_RECOVERY.md](.docs/spec/guides/emergency/METRICS_CORRUPTION_RECOVERY.md) |
| Don't understand | [FAQ.md](.docs/spec/guides/reference/FAQ.md) or [GLOSSARY.md](.docs/spec/guides/reference/GLOSSARY.md) |
| Can't find doc | (You are here! Try keywords below) |

---

## 🔑 Keywords Reference

**Looking for docs about these topics?**

- **Testing:** [testing.md](.docs/spec/canonical/specifications/testing.md), [TEST_FAILURE_GUIDE.md](.docs/spec/guides/emergency/TEST_FAILURE_GUIDE.md)
- **Architecture:** [architecture.md](.docs/spec/canonical/specifications/architecture.md), [ADR-*.md](.docs/spec/canonical/decisions/)
- **Ports & Adapters:** [ADR-003-ports-adapters-pattern.md](.docs/spec/canonical/decisions/ADR-003-ports-adapters-pattern.md)
- **Naming:** [conventions.md](.docs/spec/canonical/rules/conventions.md)
- **Threading:** [ADR-005-thread-isolation-mandatory.md](.docs/spec/canonical/decisions/ADR-005-thread-isolation-mandatory.md)
- **Import Rules:** [ia-rules.md](.docs/spec/canonical/rules/ia-rules.md) (Rule #5)
- **Documentation:** [communication.md](.docs/spec/canonical/specifications/communication.md)
- **Quality Gate:** [definition-of-done.md](.docs/spec/canonical/specifications/definition-of-done.md)
- **First Time:** [PHASE-0-AGENT-ONBOARDING.md](.docs/spec/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)
- **Now Implement:** [AGENT_HARNESS.md](.docs/spec/guides/onboarding/AGENT_HARNESS.md)

---

## 🧭 Still Can't Find It?

1. Check [FAQ.md](.docs/spec/guides/reference/FAQ.md) (most common Qs)
2. Search INDEX.md in specific layer (e.g., `CANONICAL/INDEX.md`)
3. Check [GLOSSARY.md](.docs/spec/guides/reference/GLOSSARY.md) for terminology
4. Ask team in project Slack

---

**This page:** Navigation aid
**Use it:** Whenever you need to find something specific
**Updated:** April 19, 2026
