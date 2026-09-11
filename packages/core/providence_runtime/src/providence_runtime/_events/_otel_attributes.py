"""OtelAttributes — OTEL-compatible attribute mapping derived from RuntimeEvent."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from ._runtime_event import RuntimeEvent


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
            "sdd.event": self.providence_event,
            "sdd.command": self.providence_command,
            "sdd.status": self.providence_status,
            "sdd.level": self.providence_level,
            "sdd.workspace_id": self.providence_workspace_id,
            "sdd.agent_id": self.providence_agent_id,
            "sdd.artifact_fingerprint": self.providence_artifact_fingerprint,
            "sdd.schema_version": self.providence_schema_version,
            "sdd.event_schema_version": self.providence_event_schema_version,
            "sdd.decision_source_refs": self.providence_decision_source_refs,
        }

        if self.providence_duration_ms is not None:
            attrs["sdd.duration_ms"] = self.providence_duration_ms
        if self.providence_parent_event_id:
            attrs["sdd.parent_event_id"] = self.providence_parent_event_id

        optional_attrs = [
            ("sdd.economy.tokens_input", self.providence_economy_tokens_input),
            ("sdd.economy.tokens_output", self.providence_economy_tokens_output),
            ("sdd.economy.tokens_total", self.providence_economy_tokens_total),
            (
                "sdd.economy.context_bytes_loaded",
                self.providence_economy_context_bytes_loaded,
            ),
            (
                "sdd.economy.context_budget_bytes",
                self.providence_economy_context_budget_bytes,
            ),
            (
                "sdd.economy.budget_utilization_pct",
                self.providence_economy_budget_utilization_pct,
            ),
            ("sdd.economy.compression_ratio", self.providence_economy_compression_ratio),
            ("sdd.economy.retry_count", self.providence_economy_retry_count),
            (
                "sdd.economy.reflection_count",
                self.providence_economy_reflection_count,
            ),
        ]
        for key, value in optional_attrs:
            if value is not None:
                attrs[key] = value

        if self.providence_economy_path_id:
            attrs["sdd.economy.path_id"] = self.providence_economy_path_id

        return attrs
