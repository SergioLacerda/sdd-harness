# Plugin Governance System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement M019 (Governance Federation Mandate), the `.sdd/plugins/`two-tier registry infrastructure, explicit`governance_adherence:`declarations in all internal skills, and full`/docs` coverage for the plugin federation system.

**Architecture:** Seven tasks in order. No code changes to Python packages — this is pure governance artifact work: YAML files, Markdown docs, index updates. M017 is untouched. The `.sdd/skills/`directory is untouched structurally; only`skill.yaml` files gain a new block.

**Tech Stack:** YAML, Markdown, `.sdd/` governance artifacts.

---

### Task 1: M019 in mandates source

**Files:**

- Modify: `.sdd/source/mandates/mandates.md` (append after M018)

**Step 1: Append M019 block**

Open `.sdd/source/mandates/mandates.md`. After the M018 block (currently the last entry), append exactly:

```markdown

## M019: Governance Federation

**Criticality**: high
**Customizable**: No

Any plugin or skill operating inside an SDD-governed environment MUST
perform a governance handshake before execution. The handshake declares:
identity, version, risk level, capabilities, and which mandates the
plugin commits to respecting.

Three integration modes are recognized:
- governed: full SDD governance found; HARD mandates enforced, execution
  contract required, artifacts validated
- compatible: partial governance found; plugin adapts to available rules,
  reports missing context
- standalone: no governance found; plugin operates read-only, produces
  portable artifacts, recommends SDD integration

Plugins MUST NOT override host governance silently. Plugins MUST NOT
invent SDD rules that do not exist. Plugins MUST stop or degrade safely
when governance context is missing rather than proceeding with assumptions.

Internal SDD skills (under .sdd/skills/) MUST explicitly declare
governance_adherence in their skill.yaml to reinforce this contract.
```

**Step 2: Verify**

```bash
grep -c "M019" .sdd/source/mandates/mandates.md
```

Expected: `1`

**Step 3: Commit message (do not run — list files for user)**

```
Files to stage:
  .sdd/source/mandates/mandates.md

Commit message:
feat: add M019 Governance Federation mandate to mandates source
```

---

### Task 2: M019 canonical doc

**Files:**

- Create: `docs/spec/canonical/core/mandates/M019_GOVERNANCE_FEDERATION.md`

**Step 1: Create file**

```markdown

# Mandate: Governance Federation

**ID:** M019
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** pre-execution

---

## Objective

Define how any plugin or skill declares identity, negotiates capabilities,
and adheres to host governance before execution inside an SDD-governed
environment.

---

## Requirements

1. Plugins MUST perform a governance handshake before execution
2. Handshake MUST declare: id, version, risk, capabilities, governance.mode, must_follow
3. Plugins MUST NOT override host governance silently
4. Plugins MUST NOT invent SDD rules that do not exist
5. Plugins MUST stop or degrade safely when governance context is missing
6. Plugins operating in governed mode MUST respect all HARD mandates
7. Internal SDD skills (under `.sdd/skills/`) MUST declare `governance_adherence:` in skill.yaml
8. External plugins are registered via `.sdd/plugins/registry.yaml` through agent-mediated handshake
9. GovernanceEvent MUST be emitted on registration: `type=PLUGIN_REGISTERED`
10. GovernanceEvent MUST be emitted on violation: `type=PLUGIN_GOVERNANCE_VIOLATION`

---

## Integration Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| `governed`| Full`.sdd/` governance found | HARD mandates enforced, execution contract required, artifacts validated |
| `compatible` | Partial governance found | Adapts to available rules, reports missing context, degrades safely |
| `standalone` | No governance found | Read-only by default, produces portable artifacts, recommends SDD integration |

---

## Enforcement

Agent-mediated registration writes entries to `.sdd/plugins/registry.yaml`.
See `.sdd/plugins/handshake-protocol.md` for the full registration flow.

Internal skills declare adherence explicitly in `skill.yaml`:
```yaml

governance_adherence:
  mode: governed
  respects_hard_mandates: true
  must_follow:

    - M017

    - M019

```

---

## Rationale

M017 covers execution enforcement (write scope, execution_provider, approval_gate) for
analysis plugins. M019 covers the federation layer: how any plugin enters the governance
environment, declares its contract, and negotiates operating mode. Together they ensure
plugins are both correctly declared (M019) and correctly constrained at runtime (M017).

---

## Enforcement Steps

- Verify plugin has performed governance handshake before execution
- Verify registry entry exists for plugin in `.sdd/plugins/registry.yaml`(external) or`governance_adherence:`block in`skill.yaml` (internal)
- Verify plugin respects all HARD mandates when mode=governed
- Verify GovernanceEvent emitted on registration and on violation
- Verify internal skills declare `governance_adherence:` in their skill.yaml

---

## Related

- M017: Analysis Plugin Compliance (execution enforcement, downstream)
- M015: Bidirectional Agent Handshake (complementary handshake contract)
- M016: Guardrail Non-Regression (applies to plugin-produced artifacts)
- `.sdd/plugins/registry.yaml` (external plugin registry)
- `.sdd/plugins/plugin-entry.schema.yaml` (registry entry schema)
- `.sdd/plugins/handshake-protocol.md` (registration flow)
```

**Step 2: Verify**

```bash
grep "M019" docs/spec/canonical/core/mandates/M019_GOVERNANCE_FEDERATION.md | head -1
```

Expected: `**ID:** M019`

**Step 3: Commit message**

```
Files to stage:
  docs/spec/canonical/core/mandates/M019_GOVERNANCE_FEDERATION.md

Commit message:
docs: add M019 Governance Federation canonical mandate document
```

---

### Task 3: `.sdd/plugins/` directory and artifacts

**Files:**

- Create: `.sdd/plugins/plugin-entry.schema.yaml`

- Create: `.sdd/plugins/registry.yaml`

- Create: `.sdd/plugins/handshake-protocol.md`

**Step 1: Create schema**

Create `.sdd/plugins/plugin-entry.schema.yaml`:

```yaml

# Plugin Registry Entry Schema — v1.0

# All entries in .sdd/plugins/registry.yaml must conform to this schema.

# Mandate: M019 (Governance Federation)

schema_version: "1.0"

required_fields:
  id:
    type: string
    format: kebab-case
    description: Unique plugin identifier
    example: "brainstorming"

  name:
    type: string
    description: Human-readable plugin name
    example: "Brainstorming Skill"

  version:
    type: string
    format: semver
    example: "1.0.0"

  risk:
    type: enum
    values: [read_only, read_write, controlled]
    description: >
      read_only: plugin only reads context, produces analysis artifacts.
      read_write: plugin may write artifacts within declared scope.
      controlled: plugin requires explicit approval before any write.

  skill_path:
    type: string
    description: >
      Absolute or home-relative path to the installed skill directory.
      The skill itself is not relocated — this is the governance binding only.
    example: "~/.claude/skills/brainstorming"

  capabilities:
    type: list[string]
    description: Declared capabilities — what this plugin can do
    example: ["exploratory_analysis", "option_discovery", "tradeoff_mapping"]

  governance:
    type: object
    description: Governance contract for this plugin
    fields:
      mode:
        type: enum
        values: [governed, compatible, standalone]
        description: Integration mode detected at registration time
      respects_hard_mandates:
        type: bool
      must_follow:
        type: list[string]
        description: Mandate IDs this plugin commits to respecting
        example: ["M017", "M019"]

optional_fields:
  handles:
    type: list[string]
    description: Task type classifications this plugin accepts
    example: ["exploratory_analysis", "design_session"]

  source_policy:
    type: enum
    values: [always, when_relevant, never]
    description: When the plugin should consult SDD governance sources
    default: when_relevant

  output_schema:
    type: string
    description: Path to artifact output schema (if plugin produces structured output)
    example: ".sdd/contracts/analysis-result.schema.yaml"

  registered_at:
    type: string
    format: ISO8601
    description: Timestamp written by agent at registration time

  registered_by:
    type: string
    description: Agent session identifier or user that performed registration
```

**Step 2: Create registry**

Create `.sdd/plugins/registry.yaml`:

```yaml

# Plugin Registry — SDD Governance Federation

# Version: 1.0

# Mandate: M019 (Governance Federation)

# Protocol: agent-mediated

# Schema: .sdd/plugins/plugin-entry.schema.yaml
#

# Registration protocol:

#   1. Agent detects .sdd/metadata.json in working directory → SDD governance active

#   2. Agent identifies skill in use

#   3. Agent offers registration to user

#   4. User approves

#   5. Agent validates entry against plugin-entry.schema.yaml

#   6. Agent writes entry under `entries:` below

#   7. GovernanceEvent emitted: type=PLUGIN_REGISTERED
#

# Re-registration: if entry with same id exists, agent MUST show existing

# entry and ask whether to update or skip. Never silently overwrite.
#

# Internal SDD skills (.sdd/skills/) are governed via governance_adherence:

# blocks in their own skill.yaml files. They do NOT appear here.

version: "1.0"
protocol: agent-mediated

entries: []
```

**Step 3: Create handshake protocol**

Create `.sdd/plugins/handshake-protocol.md`:

```markdown

# Plugin Registration Handshake Protocol

**Status:** Active
**Mandate:** M019 (Governance Federation)
**Schema:** `.sdd/plugins/plugin-entry.schema.yaml`
**Registry:** `.sdd/plugins/registry.yaml`

---

## Agent-Mediated Registration Flow

### Prerequisites

- Agent is operating inside a directory containing `.sdd/metadata.json`
- A skill is active or has been recently invoked

### Steps

**1. Detect governance**

Agent checks for `.sdd/metadata.json`. If present, SDD governance is active.

**2. Identify skill**

Agent identifies the active skill from invocation context (skill.yaml path or
skill name from `~/.claude/skills/<name>/`).

**3. Check registry**

Agent reads `.sdd/plugins/registry.yaml`. If an entry with matching `id` exists,
skip to **Re-registration** below.

**4. Offer registration**

Agent presents to user:
> "Skill `<id>` is not registered under SDD governance.
> Register it now? This will add an entry to `.sdd/plugins/registry.yaml`
> and emit a GovernanceEvent (type=PLUGIN_REGISTERED)."

**5. User approves**

If user declines, no entry is written. Flow ends.

**6. Extract entry data**

Agent reads the skill's `skill.yaml` and extracts:
- `id`, `name`, `version` → direct mapping
- `risk_score`→ maps to registry`risk` field
- capabilities from `outcomes`or`capabilities` field
- `handles`from`triggers` or task types

**7. Determine governance mode**

| Condition | Mode |
|-----------|------|
| `.sdd/metadata.json`present + all HARD mandates resolvable |`governed` |
| `.sdd/metadata.json`present but incomplete governance |`compatible` |
| No `.sdd/`found (should not reach this step) |`standalone` |

**8. Validate entry**

Agent validates the composed entry against `plugin-entry.schema.yaml`.
All required fields must be present. If validation fails, agent reports
missing fields and asks user to provide them.

**9. Write entry**

Agent appends the validated entry to `registry.yaml`under`entries:`.

Example entry written:
```yaml

entries:

  - id: brainstorming

    name: Brainstorming Skill
    version: "1.0.0"
    risk: read_only
    skill_path: ~/.claude/skills/brainstorming
    capabilities:

      - exploratory_analysis

      - option_discovery

      - tradeoff_mapping

      - design_session

    governance:
      mode: governed
      respects_hard_mandates: true
      must_follow:

        - M019

    handles:

      - exploratory_analysis

      - design_session

    source_policy: when_relevant
    registered_at: "2026-06-05T00:00:00Z"
    registered_by: "claude-sonnet-4-6"

```

**10. Emit GovernanceEvent**

Agent emits to `.sdd/runtime/compliance-events.jsonl`:
```json

{
  "event_type": "PLUGIN_REGISTERED",
  "plugin_id": "<id>",
  "governance_mode": "<mode>",
  "severity": "info",
  "timestamp": "<ISO8601>"
}

```

---

## Re-registration

If an entry with the same `id` already exists:

1. Agent shows the existing entry
2. Agent asks: "Entry for `<id>` already exists. Update it or skip?"
3. If update: agent replaces the entry (not append), updates `registered_at`
4. If skip: no change

Agent MUST NOT silently overwrite an existing entry.

---

## Internal Skills

Skills under `.sdd/skills/`are governed via`governance_adherence:` in their
own `skill.yaml`. They MUST NOT appear in this registry.

Their contract is enforced at load time, not at registration time.
```

**Step 4: Verify structure**

```bash
ls .sdd/plugins/
```

Expected: `handshake-protocol.md  plugin-entry.schema.yaml  registry.yaml`

**Step 5: Commit message**

```
Files to stage:
  .sdd/plugins/plugin-entry.schema.yaml
  .sdd/plugins/registry.yaml
  .sdd/plugins/handshake-protocol.md

Commit message:
feat: add .sdd/plugins/ registry infrastructure for M019 governance federation
```

---

### Task 4: `governance_adherence:` in internal skills

**Files:**

- Modify: `.sdd/skills/sdd-ask/skill.yaml`

- Modify: `.sdd/skills/sdd-compress-context/skill.yaml`

- Modify: `.sdd/skills/sdd-converge/skill.yaml`

- Modify: `.sdd/skills/sdd-correct/skill.yaml`

- Modify: `.sdd/skills/sdd-diagnose/skill.yaml`

- Modify: `.sdd/skills/sdd-review-architecture/skill.yaml`

- Modify: `.sdd/skills/sdd-stabilize/skill.yaml`

- Modify: `.sdd/skills/sdd-validate-governance/skill.yaml`

**Step 1: Read each skill.yaml to find the end of file**

For each skill, append the following block at the end of `skill.yaml`:

```yaml
governance_adherence:
  mode: governed
  respects_hard_mandates: true
  must_follow:
    - M017
    - M019
```

**Step 2: Verify (spot check)**

```bash
grep -l "governance_adherence" .sdd/skills/*/skill.yaml | wc -l
```

Expected: `8`

```bash
grep "M019" .sdd/skills/sdd-ask/skill.yaml
```

Expected: `- M019`

**Step 3: Commit message**

```
Files to stage:
  .sdd/skills/sdd-ask/skill.yaml
  .sdd/skills/sdd-compress-context/skill.yaml
  .sdd/skills/sdd-converge/skill.yaml
  .sdd/skills/sdd-correct/skill.yaml
  .sdd/skills/sdd-diagnose/skill.yaml
  .sdd/skills/sdd-review-architecture/skill.yaml
  .sdd/skills/sdd-stabilize/skill.yaml
  .sdd/skills/sdd-validate-governance/skill.yaml

Commit message:
feat: declare governance_adherence in all internal SDD skills (M019)
```

---

### Task 5: `docs/guides/plugins/` — three new documents

**Files:**

- Create: `docs/guides/plugins/plugin-governance-overview.md`

- Create: `docs/guides/plugins/registration-protocol.md`

- Create: `docs/guides/plugins/plugin-entry-reference.md`

**Step 1: Create overview**

Create `docs/guides/plugins/plugin-governance-overview.md`:

```markdown

# Plugin Governance Overview

**Status:** Active
**Mandate:** M019 (Governance Federation)
**Related:** M017 (Analysis Plugin Compliance)

---

## Central Principle

> Plugins connected to SDD Harness are autonomous within their own domain,
> but governed at the boundary. They may use their own methods, heuristics,
> and expertise, but must respect host mandates, execution contracts,
> source-of-truth hierarchy, and artifact schemas when operating inside an
> SDD-governed environment.
>
> **Internal autonomy. External compatibility.**

---

## Two-Tier Plugin Model

| Tier | Location | Governed by |
|------|----------|-------------|
| Internal SDD skills | `.sdd/skills/`|`governance_adherence:`block in`skill.yaml` |
| External plugins | Installed elsewhere (e.g. `~/.claude/skills/`) | Entry in `.sdd/plugins/registry.yaml` via agent-mediated handshake |

Internal skills are part of SDD core. They do not appear in the plugin registry.
External plugins are registered at runtime when the agent detects governance and offers registration.

---

## M017 vs M019 — Separation of Responsibility

| Mandate | Covers |
|---------|--------|
| M017 — Analysis Plugin Compliance | **Execution:** write scope, execution_provider, approval_gate for analysis plugins |
| M019 — Governance Federation | **Federation:** identity declaration, capability negotiation, integration mode for any plugin or skill |

M017 and M019 are complementary. M019 governs entry; M017 governs execution.

---

## Three Integration Modes

| Mode | When | Behavior |
|------|------|----------|
| `governed`| Full`.sdd/` governance found, all HARD mandates resolvable | HARD mandates enforced, execution contract required, artifacts validated against schema |
| `compatible`|`.sdd/` found but governance is partial or incomplete | Adapts to available rules, reports missing governance context, degrades safely |
| `standalone`| No`.sdd/` governance found | Operates read-only by default, produces portable artifacts, recommends SDD integration |

The agent determines the mode at registration time based on what governance it finds.

---

## What Plugins MUST, SHOULD, and MUST NOT Do

**MUST:**
- Perform governance handshake before execution
- Declare identity, version, risk, capabilities, and mandate commitments
- Stop or degrade safely when governance context is missing
- Respect all HARD mandates when operating in `governed` mode
- Never override host governance silently

**SHOULD:**
- Consult SDD governance sources when the task affects architecture, requirements, or public contracts
- Reuse SDD templates for outputs
- Report confidence, assumptions, and unresolved ambiguities

**MUST NOT:**
- Invent SDD rules that do not exist
- Execute write actions without declared scope
- Treat plugin-internal assumptions as project truth
- Hide uncertainty or conflicts

---

## Further Reading

- [Registration Protocol](registration-protocol.md) — step-by-step agent-mediated handshake
- [Plugin Entry Reference](plugin-entry-reference.md) — all registry entry fields
- [M019 Mandate](../../spec/canonical/core/mandates/M019_GOVERNANCE_FEDERATION.md)
- [M017 Mandate](../../spec/canonical/core/mandates/M017_ANALYSIS_PLUGIN_COMPLIANCE.md)
- [`.sdd/plugins/registry.yaml`](../../../.sdd/plugins/registry.yaml) — live registry
- [`.sdd/plugins/handshake-protocol.md`](../../../.sdd/plugins/handshake-protocol.md) — agent-facing protocol
```

**Step 2: Create registration protocol doc**

Create `docs/guides/plugins/registration-protocol.md`:

```markdown

# Plugin Registration Protocol

**Status:** Active
**Mandate:** M019 (Governance Federation)
**Agent-facing counterpart:** `.sdd/plugins/handshake-protocol.md`

---

## Overview

Plugin registration is **agent-mediated**: the agent detects SDD governance,
identifies the active skill, and offers to register it. The user approves.
The agent writes the entry to `.sdd/plugins/registry.yaml` and emits a
GovernanceEvent.

No plugin self-registers. No static pre-population. The registry reflects
what has actually been used and approved in this project.

---

## Registration Flow

```

Agent detects .sdd/metadata.json
        ↓
Agent identifies active skill
        ↓
Agent checks registry.yaml for existing entry
        ↓ (not found)
Agent offers registration to user
        ↓ (user approves)
Agent extracts data from skill.yaml
        ↓
Agent determines governance mode
  (governed / compatible / standalone)
        ↓
Agent validates entry against plugin-entry.schema.yaml
        ↓
Agent writes entry to registry.yaml
        ↓
GovernanceEvent emitted: PLUGIN_REGISTERED

```

---

## Governance Mode Determination

The agent determines mode based on what governance it finds at registration time:

| Condition | Mode assigned |
|-----------|--------------|
| `.sdd/metadata.json`present + all HARD mandates resolvable |`governed` |
| `.sdd/metadata.json`present but governance incomplete |`compatible` |
| No `.sdd/`found |`standalone` (registration deferred) |

---

## Re-registration

If an entry for the same plugin `id` already exists:

1. Agent shows the existing entry
2. Agent asks: "Entry for `<id>` already exists. Update or skip?"
3. Update: entry is replaced, `registered_at` updated
4. Skip: no change made

The agent MUST NOT silently overwrite an existing entry.

---

## GovernanceEvents

Two events are relevant to plugin governance:

| Event type | When emitted | Severity |
|------------|-------------|---------|
| `PLUGIN_REGISTERED`| Plugin successfully registered |`info` |
| `PLUGIN_GOVERNANCE_VIOLATION`| Plugin violated M019 or M017 at runtime |`critical` |

Events are written to `.sdd/runtime/compliance-events.jsonl`.

---

## Internal Skills

Skills under `.sdd/skills/` are **not registered** via this protocol. Their
governance contract is declared directly in their `skill.yaml` via the
`governance_adherence:` block. They are governed at load time, not registration time.

See [Plugin Governance Overview](plugin-governance-overview.md) for the two-tier model.
```

**Step 3: Create entry reference**

Create `docs/guides/plugins/plugin-entry-reference.md`:

```markdown

# Plugin Entry Reference

**Status:** Active
**Schema:** `.sdd/plugins/plugin-entry.schema.yaml`
**Mandate:** M019 (Governance Federation)

---

## Required Fields

### `id`
- **Type:** string (kebab-case)
- **Description:** Unique plugin identifier. Must match the skill's declared id.
- **Example:** `brainstorming`

### `name`
- **Type:** string
- **Description:** Human-readable plugin name.
- **Example:** `Brainstorming Skill`

### `version`
- **Type:** string (semver)
- **Description:** Plugin version at time of registration.
- **Example:** `1.0.0`

### `risk`
- **Type:** enum — `read_only`|`read_write`|`controlled`
- **Description:**
  - `read_only`: plugin only reads context and produces analysis artifacts
  - `read_write`: plugin may write artifacts within declared scope
  - `controlled`: plugin requires explicit user approval before any write

### `skill_path`
- **Type:** string (absolute or home-relative path)
- **Description:** Path to the installed skill directory. The skill is not moved; this is the governance binding only.
- **Example:** `~/.claude/skills/brainstorming`

### `capabilities`
- **Type:** list of strings
- **Description:** What this plugin can do — declared capability identifiers.
- **Example:** `["exploratory_analysis", "option_discovery", "tradeoff_mapping"]`

### `governance`
- **Type:** object
- **Fields:**
  - `mode`(enum:`governed`|`compatible`|`standalone`) — determined at registration time
  - `respects_hard_mandates`(bool) — must be`true`for`governed` mode
  - `must_follow` (list of mandate IDs) — mandates the plugin commits to

---

## Optional Fields

### `handles`
- **Type:** list of strings
- **Description:** Task type classifications this plugin accepts. Used for routing.
- **Example:** `["exploratory_analysis", "design_session"]`

### `source_policy`
- **Type:** enum — `always`|`when_relevant`|`never`
- **Default:** `when_relevant`
- **Description:** When the plugin consults SDD governance sources (mandates, guidelines, ADRs).

### `output_schema`
- **Type:** string (file path)
- **Description:** Path to the artifact output schema, if the plugin produces structured output.
- **Example:** `.sdd/contracts/analysis-result.schema.yaml`

### `registered_at`
- **Type:** string (ISO 8601)
- **Description:** Timestamp written by the agent at registration time.

### `registered_by`
- **Type:** string
- **Description:** Agent session or user identifier that performed registration.

---

## Complete Example Entry

```yaml

- id: brainstorming

  name: Brainstorming Skill
  version: "1.0.0"
  risk: read_only
  skill_path: ~/.claude/skills/brainstorming
  capabilities:

    - exploratory_analysis

    - option_discovery

    - tradeoff_mapping

    - design_session

  governance:
    mode: governed
    respects_hard_mandates: true
    must_follow:

      - M019

  handles:

    - exploratory_analysis

    - design_session

  source_policy: when_relevant
  registered_at: "2026-06-05T00:00:00Z"
  registered_by: "claude-sonnet-4-6"

```

---

## What Does NOT Go Here

- Internal SDD skills (`.sdd/skills/`) — governed via `governance_adherence:`in`skill.yaml`
- Plugin-instance documentation (requirements-strategist, openspec, etc.) — created when the plugin is implemented
- Governance rules — these live in mandates, not in registry entries
```

**Step 4: Verify**

```bash
ls docs/guides/plugins/
```

Expected: `plugin-entry-reference.md  plugin-governance-overview.md  registration-protocol.md`

**Step 5: Commit message**

```
Files to stage:
  docs/guides/plugins/plugin-governance-overview.md
  docs/guides/plugins/registration-protocol.md
  docs/guides/plugins/plugin-entry-reference.md

Commit message:
docs: add plugin governance guide (overview, registration protocol, entry reference)
```

---

### Task 6: Update three indices

**Files:**

- Modify: `docs/spec/canonical/core/mandates/INDEX.md`

- Modify: `docs/spec/canonical/INDEX.md`

- Modify: `docs/indices/MASTER_INDEX.md`

**Step 1: Update mandates INDEX**

In `docs/spec/canonical/core/mandates/INDEX.md`, find the table row for M017 and add M019 after it:

```markdown
| M019 | Governance Federation | [M019_GOVERNANCE_FEDERATION.md](M019_GOVERNANCE_FEDERATION.md) |
```

**Step 2: Update canonical INDEX**

In `docs/spec/canonical/INDEX.md`, after the `## 📐 Language Engineering Guidelines (M018)` section, add:

```markdown

## 🔌 Plugin Governance (M019)

*How external plugins and skills declare identity, negotiate capabilities, and adhere to host governance.*

- **Overview**: [guides/plugins/plugin-governance-overview.md](../../../docs/guides/plugins/plugin-governance-overview.md) — Federation model, M017 vs M019, integration modes
- **Registration Protocol**: [guides/plugins/registration-protocol.md](../../../docs/guides/plugins/registration-protocol.md) — Agent-mediated handshake flow
- **Entry Reference**: [guides/plugins/plugin-entry-reference.md](../../../docs/guides/plugins/plugin-entry-reference.md) — All registry entry fields
- **M019 Mandate**: [core/mandates/M019_GOVERNANCE_FEDERATION.md](./core/mandates/M019_GOVERNANCE_FEDERATION.md)
- **Live registry**: [.sdd/plugins/registry.yaml](../../../../.sdd/plugins/registry.yaml)
```

**Step 3: Update MASTER_INDEX**

In `docs/indices/MASTER_INDEX.md`, find the `## 📂 Core Pillars`section and add after the`guides/guidelines/` entry:

```markdown
- **`guides/plugins/`**: [Plugin Governance](../guides/plugins/plugin-governance-overview.md) (M019) | [Registration Protocol](../guides/plugins/registration-protocol.md) · [Entry Reference](../guides/plugins/plugin-entry-reference.md)
```

**Step 4: Verify**

```bash
grep "M019" docs/spec/canonical/core/mandates/INDEX.md
grep "Plugin Governance" docs/spec/canonical/INDEX.md
grep "guides/plugins" docs/indices/MASTER_INDEX.md
```

Expected: each returns one matching line.

**Step 5: Commit message**

```
Files to stage:
  docs/spec/canonical/core/mandates/INDEX.md
  docs/spec/canonical/INDEX.md
  docs/indices/MASTER_INDEX.md

Commit message:
docs: update indices with M019 and plugin governance guide links
```

---

### Task 7: Move analysis source file to done

**Files:**

- Move: `.analysis/pending/plugins_governance.md`→`.analysis/done/plugins_governance.md`

**Step 1: Verify source exists**

```bash
ls .analysis/pending/plugins_governance.md
```

**Step 2: Move file**

```bash
mv .analysis/pending/plugins_governance.md .analysis/done/plugins_governance.md
```

**Step 3: Verify**

```bash
ls .analysis/done/plugins_governance.md
```

**Step 4: Commit message**

```
Files to stage:
  .analysis/done/plugins_governance.md

Commit message:
chore: move plugins_governance raw analysis to done — fully integrated into governance system
```

---

## Verification Checklist

After all 7 tasks:

```bash

# M019 in mandates source
grep "M019" .sdd/source/mandates/mandates.md

# M019 canonical doc exists
ls docs/spec/canonical/core/mandates/M019_GOVERNANCE_FEDERATION.md

# .sdd/plugins/ structure
ls .sdd/plugins/

# governance_adherence in all 8 internal skills
grep -l "governance_adherence" .sdd/skills/*/skill.yaml | wc -l

# 3 plugin guide docs
ls docs/guides/plugins/

# indices updated
grep "M019" docs/spec/canonical/core/mandates/INDEX.md
grep "Plugin Governance" docs/spec/canonical/INDEX.md
grep "guides/plugins" docs/indices/MASTER_INDEX.md

# analysis moved
ls .analysis/done/plugins_governance.md
```

All commands must return non-empty output.
