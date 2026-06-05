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
