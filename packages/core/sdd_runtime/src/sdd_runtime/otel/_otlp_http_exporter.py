"""OtlpHttpExporter — stdlib-only OTLP/JSON transport."""

from __future__ import annotations

import json

from .._events import OtelAttributes, RuntimeEvent
from ._payload import _build_otlp_payload


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
