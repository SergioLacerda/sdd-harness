# SDD — Positioning FAQ

---

## What is SDD?

SDD (Spec-Driven Development) is an **executable governance platform for AI agents**.

It operates in the layer between the agent's input and output — before a decision becomes code, infrastructure, or an artifact — ensuring that the agent operates with the correct context, in compliance with the defined architecture, and within the mandates established by the team.

The problem it solves is simple to state and hard to ignore: **agents without executable governance make inconsistent decisions across sessions, ignore ADRs that have already been decided, and silently and progressively accumulate architectural drift.** SDD makes that drift detectable, auditable, and automatically rejectable in CI.

---

## What does SDD compete with?

SDD **does not compete** with:

- State management frameworks (Redux, RTK, Zustand)
- CRUD scaffolding tools (Rails, Django, CAVEMAN)
- Agent flow orchestrators (LangChain, AutoGen, CAMEL)
- UI component frameworks

SDD competes in a specific and distinct space:

| Domain | What SDD delivers |
|---|---|
| **Executable governance** | Compiled, validatable mandates — not just documentation |
| **Runtime awareness** | The agent knows the state of the environment before acting |
| **Context routing** | Indexed documentation served on demand, not loaded in bulk |
| **Workflow orchestration** | A CLI that abstracts and automates the full environment setup |
| **Architecture compliance** | Guardrails that detect and log deviations in real time |
| **Multi-agent operational alignment** | All agents and humans operate under the same set of rules |

---

## How does SDD work in practice?

SDD operates **between the agent's internal iterations** — between input and output — across four axes:

### 1. Strong governance

Mandates, guardrails, guidelines, and ADRs are compiled into validatable artifacts. The system automatically detects drift and logs every event with `trace_id`, `timestamp`, and state (`HEALTHY`, `MISCONFIGURED`, `VIOLATION`). No agent decision passes without an auditable trail.

### 2. Context quality

- **Initialization handshake** — the agent confirms it loaded the correct context before executing tasks
- **Internal confidence quiz** — a self-validation mechanism that reduces architectural hallucination
- **Drift detection** — the system compares the current state with the compiled state and flags divergences

### 3. AI-optimized documentation (4 layers)

- **Layer I — Compressed material:** dense, structured content for agent consumption, not human consumption
- **Layer II — On-demand reading:** the agent accesses context selectively, instead of loading large files at the start of every session. This directly reduces token consumption.
- **Layer III — Reactive indices with A/B/C/D paths:** the agent navigates optimized reading paths according to the task type
- **Layer IV — ADRs in internal context:** architectural decisions already made are available inline, preventing the agent from repeating resolved discussions or reverting consolidated choices

### 4. Abstraction CLI

The CLI automates configurations that would otherwise require deep technical knowledge of the internal structure, making SDD accessible without coupling to implementation details.

---

## How is SDD similar to tools like CAVEMAN?

The similarity is in a single point: **both abstract environment-configuration technical knowledge through a CLI**.

The fundamental difference is scope:

- CAVEMAN and similar tools deliver the **initial setup** — scaffolding, project structure, configured boilerplate
- SDD delivers initial setup **and** **continuous runtime compliance** — the environment validates its own architecture on every operation

---

## Are mandates configurable?

Mandates have three levels:

- **MANDATORY** — non-negotiable for the agent at runtime. The system detects and logs any deviation without exception. There is no bypass.
- **OPTIONAL** — enabled via workspace configuration
- **CUSTOMIZABLE** — base behavior can be overridden by environment variables without changing the canonical structure

---

## What happens if I run the wizard and import the full package?

You get a functional environment with pre-compiled, immediately validatable governance — not just boilerplate. The package includes:

- Ready-to-use canonical mandates (Clean Architecture, TDD, Context Awareness)
- Identified and documented anti-patterns for the agent to avoid
- Guardrails configured to automatically detect deviations
- Active telemetry trail from the first command
- Documentation indexed in four layers for efficient agent consumption

Included patterns are **language-agnostic** — they work regardless of the stack.

---

## What does telemetry deliver in practice?

Every relevant agent decision generates a JSONL event with `ts`, `event`, `command`, `state`, and `details`. This enables:

- **Full audit** of every agent session
- **Retroactive drift detection** — you know when and where the deviation occurred
- **Automated CI gate** — the pipeline can fail if compliance drops below the threshold
- **Traceability via `trace_id`** — every operation is correlatable end to end
