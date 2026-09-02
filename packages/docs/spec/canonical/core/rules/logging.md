# 📊 RULESET — Logging & Telemetry

## 🎯 Purpose

Ensure consistent observability, auditability, and distributed tracing across the agentic ecosystem.

---

## 🔒 HARD RULES

- **Structured Logs**: Debug and internal logs MUST be structured JSON.
- **Human Output**: CLI and user-facing output MUST be human-readable plain text.
- **Telemetry Emission**: Any governance-significant decision MUST emit a `RuntimeEvent`.

---

## 🔭 OPEN TELEMETRY

- **Fingerprinting**: All OTEL spans MUST include the `sdd.artifact_fingerprint`.
- **Trace Propagation**: Distributed traces MUST be preserved across agent-to-agent calls using the same `trace_id`.

---

## ❌ ANTI-PATTERNS

- **Silent Failures**: Swallowing critical errors without emitting a `fail` status event.
- **Log Pollution**: Emitting non-governance debug data as telemetry events.
- **Trace Breaking**: Generating a new `trace_id` for a sub-task instead of propagating the parent context.
