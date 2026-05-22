"""Shared event data structures — isolated to break cyclic imports.

Extracted from telemetry.py to allow alerts.py to import RuntimeEvent
without creating a telemetry ↔ alerts cycle.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---- Schema version ---------------------------------------------------------
EVENT_SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _generate_span_id() -> str:
    """Generate a unique span ID (UUID hex, truncated to 16 chars for OTLP compat)."""
    return uuid.uuid4().hex[:16]


@dataclass
class RuntimeEvent:
    """A single governance-aware runtime event.

    Mandatory fields per §13.3 envelope:
      event, command, status, trace_id, service, workspace_id, agent_id,
      artifact_fingerprint, schema_version, ts, event_schema_version.

    Operation-timing fields per §15.1 passive-mode minimum:
      start_ts, end_ts, iterations_count.
    """

    # Core identity
    event: str
    command: str
    status: str  # ok | warn | fail
    trace_id: str

    # Observability envelope
    level: str = "INFO"  # DEBUG | INFO | WARN | ERROR
    service: str = "sdd-runtime"
    workspace_id: str = ""
    agent_id: str = ""

    # Governance traceability
    artifact_fingerprint: str = ""
    schema_version: str = ""
    decision_source_refs: list[str] = field(default_factory=list)

    # Performance
    duration_ms: int | None = None

    # OTEL span context (§13 Phase C — span_id mandatory once OTEL enabled)
    # Phase 1: Auto-populate with UUID if not explicitly set
    span_id: str = field(default_factory=_generate_span_id)

    # Phase 1: Parent event ID for causality tracking across distributed operations
    parent_event_id: str = ""

    # LLM call tracking (§15.1 passive mode minimum)
    start_ts: str = ""
    end_ts: str = ""
    iterations_count: int | None = None

    # Token Economy fields (§economy/metrics.md)
    tokens_input: int | None = None
    tokens_output: int | None = None
    tokens_total: int | None = None
    context_bytes_loaded: int | None = None
    context_budget_bytes: int | None = None
    budget_utilization_pct: float | None = None
    compression_ratio: float | None = None
    retry_count: int | None = None
    reflection_count: int | None = None
    path_id: str = ""

    # Payload
    details: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    ts: str = field(default_factory=_utc_now)
    event_schema_version: str = EVENT_SCHEMA_VERSION  # §15.3 — mandatory in every event

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# OtelAttributes — OTEL-compatible attribute mapping
# ---------------------------------------------------------------------------


@dataclass
class OtelAttributes:
    """OTEL-compatible attribute set derived from a RuntimeEvent.

    Standard OTEL resource/span attributes use ``service.name`` and
    ``trace.id`` / ``span.id`` keys.  Governance-specific attributes use the
    ``sdd.*`` namespace (e.g. ``sdd.event``, ``sdd.artifact_fingerprint``).
    """

    # OTEL standard
    service_name: str
    trace_id: str
    span_id: str

    # SDD governance namespace
    sdd_event: str
    sdd_command: str
    sdd_status: str
    sdd_level: str
    sdd_workspace_id: str
    sdd_agent_id: str
    sdd_artifact_fingerprint: str
    sdd_schema_version: str
    sdd_event_schema_version: str
    sdd_decision_source_refs: str  # JSON-encoded list[str]
    sdd_duration_ms: int | None
    sdd_parent_event_id: str = ""  # Phase 1: Causality linking

    # Token Economy namespace (§economy/metrics.md — sdd.economy.*)
    sdd_economy_tokens_input: int | None = None
    sdd_economy_tokens_output: int | None = None
    sdd_economy_tokens_total: int | None = None
    sdd_economy_context_bytes_loaded: int | None = None
    sdd_economy_context_budget_bytes: int | None = None
    sdd_economy_budget_utilization_pct: float | None = None
    sdd_economy_compression_ratio: float | None = None
    sdd_economy_retry_count: int | None = None
    sdd_economy_reflection_count: int | None = None
    sdd_economy_path_id: str = ""

    @classmethod
    def from_event(cls, event: RuntimeEvent, span_id: str = "") -> OtelAttributes:
        """Map a ``RuntimeEvent`` to OTEL attributes."""
        resolved_span_id = span_id or event.span_id or uuid.uuid4().hex[:16]
        return cls(
            service_name=event.service,
            trace_id=event.trace_id,
            span_id=resolved_span_id,
            sdd_event=event.event,
            sdd_command=event.command,
            sdd_status=event.status,
            sdd_level=event.level,
            sdd_workspace_id=event.workspace_id,
            sdd_agent_id=event.agent_id,
            sdd_artifact_fingerprint=event.artifact_fingerprint,
            sdd_schema_version=event.schema_version,
            sdd_event_schema_version=event.event_schema_version,
            sdd_decision_source_refs=json.dumps(event.decision_source_refs),
            sdd_duration_ms=event.duration_ms,
            sdd_parent_event_id=event.parent_event_id,
            sdd_economy_tokens_input=event.tokens_input,
            sdd_economy_tokens_output=event.tokens_output,
            sdd_economy_tokens_total=event.tokens_total,
            sdd_economy_context_bytes_loaded=event.context_bytes_loaded,
            sdd_economy_context_budget_bytes=event.context_budget_bytes,
            sdd_economy_budget_utilization_pct=event.budget_utilization_pct,
            sdd_economy_compression_ratio=event.compression_ratio,
            sdd_economy_retry_count=event.retry_count,
            sdd_economy_reflection_count=event.reflection_count,
            sdd_economy_path_id=event.path_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_otel_dict(self) -> dict[str, Any]:
        """Return attributes as a flat dict with OTEL dotted-key names."""
        attrs: dict[str, Any] = {
            "service.name": self.service_name,
            "sdd.event": self.sdd_event,
            "sdd.command": self.sdd_command,
            "sdd.status": self.sdd_status,
            "sdd.level": self.sdd_level,
            "sdd.workspace_id": self.sdd_workspace_id,
            "sdd.agent_id": self.sdd_agent_id,
            "sdd.artifact_fingerprint": self.sdd_artifact_fingerprint,
            "sdd.schema_version": self.sdd_schema_version,
            "sdd.event_schema_version": self.sdd_event_schema_version,
            "sdd.decision_source_refs": self.sdd_decision_source_refs,
        }

        if self.sdd_duration_ms is not None:
            attrs["sdd.duration_ms"] = self.sdd_duration_ms
        if self.sdd_parent_event_id:
            attrs["sdd.parent_event_id"] = self.sdd_parent_event_id

        optional_attrs = [
            ("sdd.economy.tokens_input", self.sdd_economy_tokens_input),
            ("sdd.economy.tokens_output", self.sdd_economy_tokens_output),
            ("sdd.economy.tokens_total", self.sdd_economy_tokens_total),
            (
                "sdd.economy.context_bytes_loaded",
                self.sdd_economy_context_bytes_loaded,
            ),
            (
                "sdd.economy.context_budget_bytes",
                self.sdd_economy_context_budget_bytes,
            ),
            (
                "sdd.economy.budget_utilization_pct",
                self.sdd_economy_budget_utilization_pct,
            ),
            ("sdd.economy.compression_ratio", self.sdd_economy_compression_ratio),
            ("sdd.economy.retry_count", self.sdd_economy_retry_count),
            (
                "sdd.economy.reflection_count",
                self.sdd_economy_reflection_count,
            ),
        ]
        for key, value in optional_attrs:
            if value is not None:
                attrs[key] = value

        if self.sdd_economy_path_id:
            attrs["sdd.economy.path_id"] = self.sdd_economy_path_id

        return attrs


__all__ = [
    "RuntimeEvent",
    "EVENT_SCHEMA_VERSION",
    "OtelAttributes",
]
