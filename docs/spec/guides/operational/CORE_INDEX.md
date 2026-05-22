# 📑 EXECUTION — Local Index

**Complete navigation for the EXECUTION flow (develop using SDD AGENT_HARNESS workflow)**

---

## 📍 Entry Points

Choose your starting point:

- **New to SDD?** → [_START_HERE.md](./_START_HERE.md) (5 min orientation)
- **Looking for specific doc?** → [NAVIGATION.md](./NAVIGATION.md) (keyword search)
- **Ready to implement?** → [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md) (7-phase workflow)
- **Something broken?** → [Emergency](./docs/ia/guides/emergency/) (5 crisis procedures)

---

## 🚀 AGENT_HARNESS: 7 Phases

The complete development workflow:

| Phase | Duration | Document | Goal |
|-------|----------|----------|------|
| **PHASE 0** | 20-30 min | [PHASE-0-AGENT-ONBOARDING.md](./docs/ia/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md) | Setup `.sdd/` infrastructure (first time only) |
| **PHASE 1** | 15 min | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md#phase-1) + [constitution.md](./docs/ia/CANONICAL/rules/constitution.md) + [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) | Lock to rules, pass VALIDATION_QUIZ (≥80%) |
| **PHASE 2** | 5 min | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md#phase-2) | Check execution state for conflicts |
| **PHASE 3** | 5 min | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md#phase-3) | Choose PATH (A/B/C/D) → load right docs |
| **PHASE 4** | 10-20 min | [search-keywords.md](./docs/ia/runtime/search-keywords.md) + [spec-guides-index.md](./docs/ia/runtime/spec-guides-index.md) | Load context on-demand |
| **PHASE 5** | 1-8 hours | [CANONICAL/specifications/](./docs/ia/CANONICAL/specifications/) | Implement + tests (TDD) |
| **PHASE 6** | 10-15 min | [definition-of-done.md](./docs/ia/CANONICAL/specifications/definition-of-done.md) | Validate (tests + quality gate) |
| **PHASE 7** | 10 min | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md#phase-7) | Checkpoint + PR |

---

## 📚 Documentation Structure

### 🔴 Constitutional Layer (Immutable)
- [constitution.md](./docs/ia/CANONICAL/rules/constitution.md) — 15 immutable principles
- Status: Read once, never changes

### 🟠 Rules Layer (Mandatory)
- [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) — 16 mandatory rules
- [conventions.md](./docs/ia/CANONICAL/rules/conventions.md) — Naming, structure, patterns
- Status: Must follow for every implementation

### 🟡 Architecture Layer (Decisions)
- [ADR-001-autonomous-agents.md](./docs/ia/CANONICAL/decisions/ADR-001-autonomous-agents.md)
- [ADR-002-three-layer-architecture.md](./docs/ia/CANONICAL/decisions/ADR-002-three-layer-architecture.md)
- [ADR-003-ports-adapters-pattern.md](./docs/ia/CANONICAL/decisions/ADR-003-ports-adapters-pattern.md)
- [ADR-004-isolated-testing.md](./docs/ia/CANONICAL/decisions/ADR-004-isolated-testing.md)
- [ADR-005-thread-isolation-mandatory.md](./docs/ia/CANONICAL/decisions/ADR-005-thread-isolation-mandatory.md)
- [ADR-006-governance-automation.md](./docs/ia/CANONICAL/decisions/ADR-006-governance-automation.md)
- Status: Reference when designing or questioning decisions

### 🟢 Specifications Layer (How To)
- [architecture.md](./docs/ia/CANONICAL/specifications/architecture.md) — Overall structure
- [testing.md](./docs/ia/CANONICAL/specifications/testing.md) — Test patterns & TDD
- [feature-checklist.md](./docs/ia/CANONICAL/specifications/feature-checklist.md) — Quality gate
- [definition-of-done.md](./docs/ia/CANONICAL/specifications/definition-of-done.md) — 45+ completion criteria
- [communication.md](./docs/ia/CANONICAL/specifications/communication.md) — Docs & clarity
- Status: Follow during PHASE 5 implementation

### 🔵 Guides Layer (How To Do)
**Onboarding:**
- [PHASE-0-AGENT-ONBOARDING.md](./docs/ia/guides/onboarding/PHASE-0-AGENT-ONBOARDING.md)
- [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md)

**Operational:**
- [DEVELOPMENT_WORKFLOW_VALIDATION.md](./docs/ia/guides/operational/DEVELOPMENT_WORKFLOW_VALIDATION.md)
- [METRICS_TRACKING.md](./docs/ia/guides/operational/METRICS_TRACKING.md)
- [PRE_COMMIT_HOOKS.md](./docs/ia/guides/operational/PRE_COMMIT_HOOKS.md)

**Emergency (Crisis Procedures):**
- [README.md](./docs/ia/guides/emergency/README.md) — Pick your emergency
- [PRE_COMMIT_HOOK_FAILURE.md](./docs/ia/guides/emergency/PRE_COMMIT_HOOK_FAILURE.md)
- [TEST_FAILURE_GUIDE.md](./docs/ia/guides/emergency/TEST_FAILURE_GUIDE.md)
- [RULES_VIOLATION_DETECTED.md](./docs/ia/guides/emergency/RULES_VIOLATION_DETECTED.md)
- [IMPORTS_CORRUPTED.md](./docs/ia/guides/emergency/IMPORTS_CORRUPTED.md)
- [METRICS_CORRUPTION_RECOVERY.md](./docs/ia/guides/emergency/METRICS_CORRUPTION_RECOVERY.md)

**Reference:**
- [FAQ.md](./docs/ia/guides/reference/FAQ.md) — Common questions
- [GLOSSARY.md](./docs/ia/guides/reference/GLOSSARY.md) — Terminology
- [HOW_EACH_LAYER_WORKS.md](./docs/ia/guides/reference/HOW_EACH_LAYER_WORKS.md) — Deep dives

### 🟣 Runtime Layer (Search Indices)
- [search-keywords.md](./docs/ia/runtime/search-keywords.md) — Find docs by topic
- [spec-canonical-index.md](./docs/ia/runtime/spec-canonical-index.md) — CANONICAL/ docs
- [spec-guides-index.md](./docs/ia/runtime/spec-guides-index.md) — guides/ docs

### ⚫ Custom / Project Layer
- `docs/ia/custom/[YOUR_PROJECT]/` — Project-specific specs + execution state

---

## 🔍 Find by Task

| I want to... | Read this |
|--------------|-----------|
| Understand what SDD is | [constitution.md](./docs/ia/CANONICAL/rules/constitution.md) (5 min) |
| Pass the VALIDATION_QUIZ | [ia-rules.md](./docs/ia/CANONICAL/rules/ia-rules.md) (must get ≥80%) |
| Implement a feature | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md) → PHASE 5 |
| Fix a bug | [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md) → PATH A |
| Write tests | [testing.md](./docs/ia/CANONICAL/specifications/testing.md) |
| Check my work | [definition-of-done.md](./docs/ia/CANONICAL/specifications/definition-of-done.md) |
| Understand architecture | [architecture.md](./docs/ia/CANONICAL/specifications/architecture.md) |
| Ask a question | [FAQ.md](./docs/ia/guides/reference/FAQ.md) |
| Find a specific doc | [NAVIGATION.md](./NAVIGATION.md) (keyword search) |
| Emergency | [Emergency/README.md](./docs/ia/guides/emergency/README.md) |

---

## 🧭 By Role

**👨‍💻 Individual Contributor / Developer**
```
_START_HERE.md
  ↓
AGENT_HARNESS.md (PHASE 1-7)
  ↓
CANONICAL/specifications/
  ↓
Implement + tests
```

**🤖 AI Agent / Automation**
```
PHASE-0-AGENT-ONBOARDING.md (setup)
  ↓
ia-rules.md (must pass ≥80%)
  ↓
AGENT_HARNESS.md (full workflow)
  ↓
Implement
```

**🆘 Someone in Crisis**
```
Emergency/README.md
  ↓
Pick specific crisis guide
  ↓
Follow steps
```

---

## ✅ Success Criteria

| Goal | Success = |
|------|-----------|
| Feature implemented | Code written + committed |
| Tests passing | 100% coverage for new code |
| Quality gate | Definition of done (45+ items) checked |
| Knowledge captured | `.sdd/context-aware/` docs updated |
| Ready for review | PR with checkpoint + decisions documented |

---

## 🚀 Next Steps

1. **New?** → [_START_HERE.md](./_START_HERE.md)
2. **Ready to code?** → [AGENT_HARNESS.md](./docs/ia/guides/onboarding/AGENT_HARNESS.md)
3. **Specific question?** → [NAVIGATION.md](./NAVIGATION.md)
4. **In trouble?** → [Emergency/README.md](./docs/ia/guides/emergency/README.md)

---

**Purpose:** EXECUTION flow index
**Target:** Developers/agents using workflow
**Status:** Ready
**Last updated:** April 19, 2026
