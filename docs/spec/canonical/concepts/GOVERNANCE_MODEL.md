# Governance Model: Immutable Kernel vs Selectable Features

**Purpose:** Define the segregation between the core system logic (Immutable) and the project-specific rules (Selectable).

---

## 🏗️ The Segregation Model

### 1. The Immutable Kernel (`spec/canonical/core/`)
These documents form the DNA of the Agentic OS. They are **MANDATORY** for any project using this framework.
- **Goal**: System stability, context continuity, and operational safety.
- **Mandates**: `CONTEXT_AWARENESS` (M003).
- **Cognition**: All decision models and context loading strategies.
- **Entrypoint**: `AGENT_ENTRYPOINT.md`.

> ⚠️ **Compiler Rule**: Always include 100% of the `core/` directory in the generated AI core.

---

### 2. The Selectable Features (`spec/canonical/features/`)
These documents represent the architectural and quality choices available to the client.
- **Goal**: Customization and project-specific excellence.
- **Mandates**: `CLEAN_ARCHITECTURE` (M001), `TDD` (M002), `API_STANDARDS`, etc.
- **Modes**:
    - `[MANDATORY]`: Client must follow this (e.g., Compliance).
    - `[OPTIONAL]`: Client can opt-in (e.g., TDD).
    - `[CUSTOMIZABLE]`: Client can modify the rule (e.g., Naming Conventions).

---

## 🔁 Selection Workflow

1. **Discovery**: User reviews the `features/` directory.
2. **Flagging**: User creates a `selection.json` or equivalent marking their choices.
3. **Compilation**: The system generator pulls:
    - ALL files from `core/`.
    - SELECTED files from `features/`.
4. **Agent Boot**: The resulting compressed core is provided to the agent as its primary instruction set.

---

## ✅ Stability Levels

| Level | Definition | Can be removed? |
|---|---|---|
| **IMMUTABLE** | Core logic of the Agentic OS | ❌ No |
| **STABLE** | Standard industry best practices | ✅ Yes (Optional) |
| **BETA/CUSTOM** | Experimental or specific project logic | ✅ Yes |
