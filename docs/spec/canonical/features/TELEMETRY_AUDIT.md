# Mandate: Telemetry & Audit Trail

**Type:** CORE FEATURE / HARD MANDATE
**ID:** M007
**Category:** Observability

---

## 🎯 Goal

Provide an industrial-grade, immutable audit trail of all agentic decisions, ensuring accountability and real-time monitoring of governance compliance.

---

## 📜 Requirement

The system MUST implement a dual-sink telemetry architecture:

1.  **Local Audit Trail (Canonical)**:
    *   Structured JSONL events persisted to `.sdd/audit-trail/compliance-events.jsonl`.
    *   Mandatory persistence for all governance violations and budget breaches.
    *   Support for task-scoped segmentation (work-item segmentation).

2.  **OpenTelemetry Bridge (Global)**:
    *   Asynchronous export of events to any OTLP-compliant backend.
    *   Standardized `sdd.*` attribute mapping for governance metrics.
    *   Zero-dependency implementation using Python standard library.

---

## ⚖️ Rationale

In autonomous agent systems, "black box" behavior is a catastrophic risk. This feature ensures that every decision point is recorded with its associated governance context (fingerprint, mandates loaded, budget state), making every agent action auditable and transparent.

---

## ✅ Validation

- [ ] Every agent command emits a `runtime.session.start` event.
- [ ] Budget breaches (≥100%) trigger an immediate `economy.budget.breach` event.
- [ ] Trace IDs are propagated across the session to link related operations.
- [ ] Events successfully export to OTEL backends when configured.
