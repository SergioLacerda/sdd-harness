"""OTEL mapping layer — §13 Phase C opt-in OpenTelemetry bridge.

This module is zero-dependency by default.  The ``OtlpHttpExporter`` uses only
stdlib ``urllib.request`` so no additional packages are required.  If the
caller prefers the official ``opentelemetry-sdk``, they can implement the
``OtelExporter`` protocol and pass it to ``OtelBridge``.

Architecture
------------
::

    RuntimeEvent
        │
        ▼
    OtelAttributes.from_event()          ← pure mapping, no I/O
        │
        ▼
    OtelExporter.export(event, attrs)    ← transport abstraction
        │
    OtlpHttpExporter                     ← stdlib urllib, OTLP JSON format

``OtelBridge`` wraps ``TelemetrySink`` and calls the exporter on every
``emit()``.  The JSONL sink is always written first; OTEL export is
best-effort.  If the exporter raises, the event is silently dropped on the
OTEL side — JSONL remains the source of truth.

Usage example
-------------
::

    from sdd_runtime import OtelBridge
    from sdd_runtime.otel import OtlpHttpExporter

    exporter = OtlpHttpExporter(
        endpoint="https://api.datadoghq.com/api/v0.2/traces",
        headers={"DD-API-KEY": "..."},
    )
    sink = OtelBridge(exporter=exporter, jsonl_path=Path(".sdd/runtime/events.jsonl"))
    sink.emit(RuntimeEvent(event="governance.compile", command="compile", ...))
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from ._events import OtelAttributes, RuntimeEvent

# ---------------------------------------------------------------------------
# OTEL payload helpers
# ---------------------------------------------------------------------------


def _ts_to_nano(ts: str) -> int:
    """Convert an ISO-8601 string to Unix nanoseconds.  Returns 0 on failure."""
    if not ts:
        return 0
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return 0


def _status_code(status: str) -> int:
    """Map an SDD status string to an OTLP span status code integer."""
    return {"ok": 1, "warn": 1, "fail": 2}.get(status.lower(), 0)


def _to_kv_list(attrs: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a flat dict to the OTLP ``KeyValue`` list format."""
    result: list[dict[str, Any]] = []
    for key, value in attrs.items():
        if isinstance(value, bool):
            result.append({"key": key, "value": {"boolValue": value}})
        elif isinstance(value, int):
            result.append({"key": key, "value": {"intValue": value}})
        elif isinstance(value, float):
            result.append({"key": key, "value": {"doubleValue": value}})
        else:
            result.append({"key": key, "value": {"stringValue": str(value)}})
    return result


def _build_otlp_payload(event: RuntimeEvent, attrs: OtelAttributes) -> dict[str, Any]:
    """Build a minimal OTLP/JSON resourceSpans payload for a single span."""
    start_ns = _ts_to_nano(event.ts)
    end_ts = event.end_ts if event.end_ts else event.ts
    end_ns = _ts_to_nano(end_ts)

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": _to_kv_list({"service.name": attrs.service_name}),
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "sdd-runtime", "version": "1.0"},
                        "spans": [
                            {
                                "traceId": attrs.trace_id,
                                "spanId": attrs.span_id,
                                "name": attrs.sdd_event,
                                "kind": 1,  # SPAN_KIND_INTERNAL
                                "startTimeUnixNano": start_ns,
                                "endTimeUnixNano": end_ns,
                                "attributes": _to_kv_list(attrs.to_otel_dict()),
                                "status": {
                                    "code": _status_code(attrs.sdd_status),
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }


# ---------------------------------------------------------------------------
# OtelExporter protocol — implement to add any OTEL-compatible backend
# ---------------------------------------------------------------------------


@runtime_checkable
class OtelExporter(Protocol):
    """Minimal transport protocol for OTEL event export."""

    def export(self, event: RuntimeEvent, attrs: OtelAttributes) -> None:
        """Export a single event with its OTEL-mapped attributes."""
        pass

    def shutdown(self) -> None:
        """Release resources (connections, buffers, etc.)."""
        pass


# ---------------------------------------------------------------------------
# OtlpHttpExporter — stdlib-only OTLP/JSON transport
# ---------------------------------------------------------------------------


class OtlpHttpExporter:
    """Export ``RuntimeEvent`` spans to any OTLP-HTTP/JSON endpoint.

    Supports Datadog (via ``/api/v0.2/traces``), Grafana, Jaeger, or any
    OpenTelemetry Collector with HTTP/JSON ingestion enabled.

    This exporter is intentionally minimal: it sends one span per event,
    uses stdlib ``urllib.request``, and swallows all network errors.  For
    production use with batching, retry, and TLS validation consider wrapping
    the official ``opentelemetry-exporter-otlp-proto-http`` package.

    Parameters
    ----------
    endpoint:
        Full OTLP HTTP URL, e.g. ``https://otelcol.example.com:4318/v1/traces``.
    headers:
        Additional HTTP headers (e.g. ``{"DD-API-KEY": "..."}``)
    timeout:
        Socket timeout in seconds (default: 5).
    """

    def __init__(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        timeout: int = 5,
    ) -> None:
        self._endpoint = endpoint
        self._headers = headers or {}
        self._timeout = timeout

    def export(self, event: RuntimeEvent, attrs: OtelAttributes) -> None:
        """POST a single OTLP-JSON span to the configured endpoint."""
        import urllib.request
        from urllib.parse import urlparse

        # Validate endpoint scheme (reject file:// and other unsafe schemes)
        parsed = urlparse(self._endpoint)
        if parsed.scheme not in ("http", "https"):
            return  # Silently skip non-HTTP(S) endpoints

        payload = _build_otlp_payload(event, attrs)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self._endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        for key, value in self._headers.items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # nosec B310
                resp.read()
        except Exception:  # nosec B110 — best-effort OTEL delivery, failure is non-critical
            pass

    def shutdown(self) -> None:
        """Shutdown."""
        pass  # No persistent connections to close
