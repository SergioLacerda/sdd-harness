"""Telemetry engine — typed runtime events with optional JSONL persistence.

Event schema is aligned with the Datadog-inspired envelope defined in §13.3
of the improvement plan.  The canonical audit sink is the JSONL file at
``.sdd/runtime/compliance-events.jsonl``; the sink path is caller-supplied so
the package remains zero-dependency.
"""

from __future__ import annotations

import contextlib
import logging
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ._events import (  # noqa: F401 — re-exported for backward compat
    EVENT_SCHEMA_VERSION,
    OtelAttributes,
    RuntimeEvent,
)

logger: logging.Logger = logging.getLogger(__name__)

__all__ = [
    "EVENT_SCHEMA_VERSION",
    "RuntimeEvent",
    "TelemetrySink",
    "OtelAttributes",
    "OtelBridge",
    "create_sink",
    "MODE_PASSIVE",
    "MODE_ACTIVE",
    "MODE_STRICT",
    "ECONOMY_BUDGET_WARN",
    "ECONOMY_BUDGET_BREACH",
    "ECONOMY_COMPRESSION_SKIP",
    "ECONOMY_RETRY_CAP_REACHED",
]

if TYPE_CHECKING:
    from .alerts import AlertDispatcher

# ---- Logging modes (SOFT governance parameter §13.5) ------------------------
MODE_PASSIVE = "passive"
MODE_ACTIVE = "active"
MODE_STRICT = "strict"

# ---- Economy event types (§economy/metrics.md) ------------------------------
ECONOMY_BUDGET_WARN = "economy.budget.warn"
ECONOMY_BUDGET_BREACH = "economy.budget.breach"
ECONOMY_COMPRESSION_SKIP = "economy.compression.skip"
ECONOMY_RETRY_CAP_REACHED = "economy.retry.cap.reached"

# ---- Budget zone thresholds (§economy/execution-budget.md) ------------------
_ZONE_RED_PCT: float = 90.0  # > this → RED (emit warn; MUST compress)
_ZONE_BREACH_PCT: float = 100.0  # >= this → BREACH (emit breach; block loading)

# ---- PATH context budget ceilings (§economy/execution-budget.md) ------------
# A=40 KB, B=45 KB, C=85 KB, D=35 KB/thread
_PATH_BUDGET_BYTES: dict[str, int] = {
    "A": 40 * 1024,
    "B": 45 * 1024,
    "C": 85 * 1024,
    "D": 35 * 1024,
}

# ---- Mandatory minimum events (always emitted regardless of logging_mode) ---
_MANDATORY_EVENTS = frozenset(
    {
        "governance.violation",
        "runtime.drift.detected",
        "policy.validation.fail",
        "runtime.session.start",
        "governance.ask",
        "governance.ask.full",
        ECONOMY_BUDGET_BREACH,
    }
)


class TelemetrySink:
    """Collects runtime events; optionally persists them to a JSONL file.

    Parameters
    ----------
    jsonl_path:
        Base path for the JSONL file.  When *segment_by_work_item* is True,
        events are written to ``{jsonl_path.parent}/{work_item_id}.jsonl``
        instead of directly to *jsonl_path*.
    logging_mode:
        Controls verbosity.  In ``passive`` mode only mandatory events are
        written to the JSONL file; all events remain in the in-memory list.
    segment_by_work_item:
        When True, segment the JSONL output by ``work_item_id`` from each
        event's ``details`` dict (§15.1 item 5 — task-scoped segmentation).
    agent_id:
        Identifier for the agent/CLI instance emitting events. If not provided,
        defaults to ``SDD_AGENT_ID`` environment variable or "unknown".
    alert_dispatcher:
        Fase 2: Optional AlertDispatcher for event-triggered webhooks.
        Dispatch is best-effort; all exceptions suppressed.
    """

    def __init__(
        self,
        jsonl_path: Path | None = None,
        logging_mode: str = MODE_PASSIVE,
        segment_by_work_item: bool = False,
        agent_id: str | None = None,
        alert_dispatcher: AlertDispatcher | None = None,
    ) -> None:
        import uuid

        self._events: list[RuntimeEvent] = []
        self._jsonl_path = jsonl_path
        self._logging_mode = logging_mode
        self._segment_by_work_item = segment_by_work_item
        # Phase 0 fix: Populate agent_id from parameter, env var, or session UUID
        self._agent_id = (
            agent_id
            or os.environ.get("SDD_AGENT_ID")
            or f"session-{str(uuid.uuid4())[:8]}"
        )
        # Fase 2: optional alert dispatcher (best-effort side-car)
        self._alert_dispatcher = alert_dispatcher

    def emit(self, event: RuntimeEvent) -> None:
        """Record *event* in memory and conditionally persist to JSONL."""
        # Phase 0 fix: Populate agent_id if not already set
        if not event.agent_id:
            event.agent_id = self._agent_id
        self._enrich_economy(event)
        self._events.append(event)
        if self._jsonl_path is not None:
            self._write_jsonl(event)
        self._maybe_emit_zone_event(event)
        # Fase 2: alert dispatch is best-effort, never blocks or raises
        if self._alert_dispatcher is not None:
            with contextlib.suppress(Exception):
                self._alert_dispatcher.on_event(event)

    def list_events(self) -> list[RuntimeEvent]:
        """List Events."""
        return list(self._events)

    def flush(self) -> None:
        """Force-write all pending in-memory events to the JSONL sink.

        No-op when no *jsonl_path* is configured.
        """
        if self._jsonl_path is None:
            return
        for evt in self._events:
            self._write_jsonl(evt)

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _enrich_economy(event: RuntimeEvent) -> None:
        """Auto-populate derived economy fields when source data is available.

        Mutates *event* in place before it is appended to the in-memory list
        and written to the JSONL sink.  All derivations are idempotent — a
        field that is already set is never overwritten.
        """
        # 1. Derive context_budget_bytes from path_id when not explicitly set.
        if event.context_budget_bytes is None and event.path_id in _PATH_BUDGET_BYTES:
            event.context_budget_bytes = _PATH_BUDGET_BYTES[event.path_id]

        # 2. Compute budget_utilization_pct from byte counts.
        if (
            event.budget_utilization_pct is None
            and event.context_bytes_loaded is not None
            and event.context_budget_bytes is not None
            and event.context_budget_bytes > 0
        ):
            event.budget_utilization_pct = round(
                event.context_bytes_loaded / event.context_budget_bytes * 100, 2
            )

        # 3. Compute tokens_total from input + output when not set.
        if (
            event.tokens_total is None
            and event.tokens_input is not None
            and event.tokens_output is not None
        ):
            event.tokens_total = event.tokens_input + event.tokens_output

    def _maybe_emit_zone_event(self, source_event: RuntimeEvent) -> None:
        """Auto-emit economy.budget.warn, economy.budget.breach, or economy.compression.skip.

        Fires after the source event is already recorded.  Zone events are
        appended directly (bypassing :meth:`emit`) to prevent recursion.
        Only fires when *budget_utilization_pct* is known and the source
        event itself is not already a zone event.
        """
        pct = source_event.budget_utilization_pct
        if pct is None:
            return
        # Do not emit zone events for zone events (prevent infinite recursion).
        if source_event.event in (
            ECONOMY_BUDGET_WARN,
            ECONOMY_BUDGET_BREACH,
            ECONOMY_COMPRESSION_SKIP,
        ):
            return

        if pct >= _ZONE_BREACH_PCT:
            zone_event_name = ECONOMY_BUDGET_BREACH
        elif pct > _ZONE_RED_PCT:
            zone_event_name = ECONOMY_BUDGET_WARN
        elif 70.0 <= pct <= _ZONE_RED_PCT and source_event.compression_ratio is None:
            # YELLOW zone and no compression occurred — emit skip event
            zone_event_name = ECONOMY_COMPRESSION_SKIP
        else:
            return  # GREEN zone or YELLOW with compression already applied

        zone_event = RuntimeEvent(
            event=zone_event_name,
            command=source_event.command,
            status="warn" if zone_event_name != ECONOMY_COMPRESSION_SKIP else "info",
            trace_id=source_event.trace_id,
            workspace_id=source_event.workspace_id,
            agent_id=source_event.agent_id or self._agent_id,
            artifact_fingerprint=source_event.artifact_fingerprint,
            schema_version=source_event.schema_version,
            path_id=source_event.path_id,
            context_bytes_loaded=source_event.context_bytes_loaded,
            context_budget_bytes=source_event.context_budget_bytes,
            budget_utilization_pct=pct,
            details={"source_event": source_event.event},
        )
        self._events.append(zone_event)
        if self._jsonl_path is not None:
            self._write_jsonl(zone_event)

    def _should_persist(self, event: RuntimeEvent) -> bool:
        if self._logging_mode in (MODE_ACTIVE, MODE_STRICT):
            return True
        # passive — only mandatory events
        return event.event in _MANDATORY_EVENTS

    def _resolve_path(self, event: RuntimeEvent) -> Path:
        """Return the actual JSONL file path, respecting work_item segmentation."""
        assert self._jsonl_path is not None
        if not self._segment_by_work_item or not event.details.get("work_item_id"):
            return self._jsonl_path
        work_item_id = str(event.details["work_item_id"])
        # Sanitise to prevent path traversal.
        safe_id = "".join(c for c in work_item_id if c.isalnum() or c in "-_")
        return self._jsonl_path.parent / f"{safe_id}.jsonl"

    def _write_jsonl(self, event: RuntimeEvent) -> None:
        if not self._should_persist(event):
            return
        target = self._resolve_path(event)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")


# OtelAttributes moved to _events.py to break cyclic import cycle with otel.py


# ---------------------------------------------------------------------------
# OtelBridge — TelemetrySink subclass with opt-in OTEL export
# ---------------------------------------------------------------------------


class OtelBridge(TelemetrySink):
    """A ``TelemetrySink`` that additionally exports events via OTEL.

    Parameters
    ----------
    exporter:
        An ``OtelExporter`` instance.  Pass ``None`` to disable OTEL export
        (bridge becomes a transparent ``TelemetrySink`` pass-through).
    **kwargs:
        Forwarded to ``TelemetrySink.__init__()`` (``jsonl_path``,
        ``logging_mode``, ``segment_by_work_item``).
    """

    def __init__(
        self,
        exporter: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._exporter = exporter

    def emit(self, event: RuntimeEvent) -> None:
        """Persist event to JSONL then export to OTEL (best-effort)."""
        super().emit(event)
        if self._exporter is None:
            return

        span_id = event.span_id or uuid.uuid4().hex[:16]
        attrs = OtelAttributes.from_event(event, span_id=span_id)
        # OTEL export is best-effort; JSONL is source of truth
        with contextlib.suppress(Exception):
            self._exporter.export(event, attrs)

    def shutdown(self) -> None:
        """Shut down the exporter and release any held resources."""
        if self._exporter is not None:
            with contextlib.suppress(Exception):
                self._exporter.shutdown()


# ---------------------------------------------------------------------------
# Factory function for Sink creation (Phase 1 Activation)
# ---------------------------------------------------------------------------


def create_sink(
    jsonl_path: Path | None = None,
    logging_mode: str = MODE_PASSIVE,
    segment_by_work_item: bool = False,
    agent_id: str | None = None,
) -> TelemetrySink:
    """Create a TelemetrySink or OtelBridge based on environment configuration.

    Activation via environment variables:
      - SDD_OTEL_EXPORTER_ENDPOINT: Full OTLP HTTP endpoint (e.g., https://...)
        When set, returns OtelBridge; when unset, returns TelemetrySink.
      - SDD_OTEL_API_KEY: Optional API key header (e.g., for Datadog DD-API-KEY).
      - SDD_AGENT_ID: Agent identifier (fallback in TelemetrySink.__init__).
      - SDD_WEBHOOK_URL: Fase 2 — webhook destination for alert dispatch.
        When set, configures AlertDispatcher for event-triggered webhooks.

    Returns TelemetrySink (default) or OtelBridge (if endpoint is configured).

    Phase 1 implementation: Makes OTEL export opt-in via env var, preserving
    JSONL local-first semantics. OTEL is best-effort; JSONL is source of truth.

    Fase 2 implementation: Optionally wires AlertDispatcher for event-triggered
    webhook dispatch (best-effort side-car, all exceptions suppressed).
    """

    # Fase 2: Try to wire alert dispatcher from env
    alert_dispatcher = None
    try:
        from .alerts import AlertDispatcher as AlertDispatcherClass

        alert_dispatcher = AlertDispatcherClass.from_env()
    except Exception:  # nosec B110 — intentional: alerts are optional, telemetry continues without them
        logger.debug(
            "Alert dispatcher unavailable; telemetry will continue without alerts",
            exc_info=True,
        )

    # Check if OTEL is configured
    otel_endpoint = os.environ.get("SDD_OTEL_EXPORTER_ENDPOINT", "").strip()

    # If no endpoint configured, return plain TelemetrySink with optional alert dispatcher
    if not otel_endpoint:
        return TelemetrySink(
            jsonl_path=jsonl_path,
            logging_mode=logging_mode,
            segment_by_work_item=segment_by_work_item,
            agent_id=agent_id,
            alert_dispatcher=alert_dispatcher,
        )

    # Endpoint is configured — use OtelBridge
    try:
        from .otel import OtlpHttpExporter

        # Prepare optional headers
        headers: dict[str, str] = {}
        api_key = os.environ.get("SDD_OTEL_API_KEY", "").strip()
        if api_key:
            # Auto-detect if endpoint looks like Datadog (use DD-API-KEY)
            parsed_url = urlparse(otel_endpoint)
            hostname = (parsed_url.hostname or "").lower()
            if hostname == "datadoghq.com" or hostname.endswith(".datadoghq.com"):
                headers["DD-API-KEY"] = api_key
            else:
                # Generic OTEL uses Authorization header
                headers["Authorization"] = f"Bearer {api_key}"

        exporter = OtlpHttpExporter(endpoint=otel_endpoint, headers=headers)
        sink = OtelBridge(
            exporter=exporter,
            jsonl_path=jsonl_path,
            logging_mode=logging_mode,
            segment_by_work_item=segment_by_work_item,
            agent_id=agent_id,
            alert_dispatcher=alert_dispatcher,
        )
        return sink
    except Exception as exc:
        # Fallback to plain TelemetrySink if OTel setup fails
        logger.warning(
            "Failed to initialize OTelBridge (%s); falling back to TelemetrySink", exc
        )
        return TelemetrySink(
            jsonl_path=jsonl_path,
            logging_mode=logging_mode,
            segment_by_work_item=segment_by_work_item,
            agent_id=agent_id,
            alert_dispatcher=alert_dispatcher,
        )
