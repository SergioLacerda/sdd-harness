# 🧠 CORE MANDATES — Runtime Contract

## 🎯 Purpose

Define mandatory behavioral contracts that ALL agents MUST follow.

---

## 🧬 Mandate Model

## Mandate Registry

| ID   | Title                          | File                          |
|------|--------------------------------|-------------------------------|
| M003 | Context Awareness & Task Caching | [M003_CONTEXT_AWARENESS.md](M003_CONTEXT_AWARENESS.md) |
| M005 | Token Economy Enforcement      | [M005_TOKEN_ECONOMY.md](M005_TOKEN_ECONOMY.md) |
| M007 | Telemetry Enforcement          | [M007_TELEMETRY.md](M007_TELEMETRY.md) |
| M008 | Audit Integrity                | [M008_AUDIT_INTEGRITY.md](M008_AUDIT_INTEGRITY.md) |
| M009 | OpenTelemetry Compliance       | [M009_OTEL_COMPLIANCE.md](M009_OTEL_COMPLIANCE.md) |
| M010 | Delivery Hygiene Enforcement   | [M010_DELIVERY_HYGIENE.md](M010_DELIVERY_HYGIENE.md) |
| M011 | English Language Standard      | [M011_LANGUAGE_STANDARD_ENGLISH.md](M011_LANGUAGE_STANDARD_ENGLISH.md) |

---

## Mandate Model

Each mandate is defined as an operational unit:

```json
{
  "id": "MXXX",
  "name": "string",
  "type": "MANDATE",
  "enforcement": "HARD",
  "required": true,
  "phase": ["pre-execution", "execution", "post-execution"],
  "actions": [],
  "validation": [],
  "failure_mode": "DEGRADED | BLOCKED"
}
