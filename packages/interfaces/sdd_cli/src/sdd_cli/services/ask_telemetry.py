"""Telemetry/session helpers for ask command flows."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

from sdd_runtime import (
    OtelBridge,
    RuntimeEvent,
    SessionManager,
    SessionState,
    TelemetrySink,
)
from sdd_runtime.otel import OtlpHttpExporter

from sdd_cli.utils.telemetry_paths import resolve_compliance_events_path


class _EventSink(Protocol):
    def emit(self, event: RuntimeEvent) -> None:
        pass


def resolve_tokens(query: str, output_text: str) -> tuple[int | None, int | None, str]:
    """Resolve token counts with explicit source.

    Source precedence:
    - env: `SDD_TOKENS_INPUT` / `SDD_TOKENS_OUTPUT` (canonical)
    - estimated: byte-based fallback (`len(text)//4`)
    """
    try:
        t_in = os.environ.get("SDD_TOKENS_INPUT", "").strip()
        t_out = os.environ.get("SDD_TOKENS_OUTPUT", "").strip()
        tokens_in: int | None = (
            int(t_in) if t_in.isdigit() else (len(query) // 4 or None)
        )
        tokens_out: int | None = (
            int(t_out) if t_out.isdigit() else (len(output_text) // 4 or None)
        )
        source = "env" if t_in.isdigit() or t_out.isdigit() else "estimated"
        return tokens_in, tokens_out, source
    except Exception:
        return None, None, "unknown"


def emit_ask_telemetry(
    event_name: str,
    *,
    command: str,
    workspace_root: Path,
    trace_id: str,
    agent_id: str,
    fingerprint: str,
    context_source: str,
    mandates_count: int,
    profile: str,
    state: str,
    drift_detected: bool,
    query_hash: str = "",
    path_id: str = "",
    start_ts: str = "",
    end_ts: str = "",
    duration_ms: int | None = None,
    context_bytes_loaded: int | None = None,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    retry_count: int | None = None,
    compression_ratio: float | None = None,
    extra_details: dict[str, Any] | None = None,
    logger: Any | None = None,
    telemetry_sink_cls: type[TelemetrySink] = TelemetrySink,
    otel_bridge_cls: type[OtelBridge] = OtelBridge,
    otlp_exporter_cls: type[OtlpHttpExporter] = OtlpHttpExporter,
) -> None:
    """Emit a typed RuntimeEvent to canonical JSONL sink. Best-effort."""
    try:
        import configparser

        events_path = resolve_compliance_events_path(workspace_root=workspace_root)
        workspace_id = "unknown"
        profile_path = workspace_root / ".sdd" / "profile"
        if profile_path.exists():
            try:
                parser = configparser.ConfigParser()
                parser.read(profile_path)
                workspace_id = parser.get("sdd", "workspace_id", fallback="unknown")
            except Exception as exc:
                if logger is not None:
                    logger.debug("Failed to read config: %s", exc)

        details: dict[str, Any] = {
            "context_source": context_source,
            "mandates_loaded": mandates_count,
            "drift_detected": drift_detected,
            "ahp_state": state,
            "profile": profile,
        }
        if query_hash:
            details["query_hash"] = query_hash
        if extra_details:
            details.update(extra_details)

        status = "ok" if state in ("HEALTHY", "PARTIAL") else "warn"
        otel_endpoint = os.environ.get("SDD_OTEL_ENDPOINT", "").strip()
        sink: _EventSink
        if otel_endpoint:
            exporter = otlp_exporter_cls(endpoint=otel_endpoint)
            sink = otel_bridge_cls(exporter=exporter, jsonl_path=events_path)
        else:
            sink = telemetry_sink_cls(jsonl_path=events_path, logging_mode="passive")
        sink.emit(
            RuntimeEvent(
                event=event_name,
                command=command,
                status=status,
                trace_id=trace_id,
                workspace_id=workspace_id,
                agent_id=agent_id,
                artifact_fingerprint=fingerprint,
                decision_source_refs=["sdd-governance-context"],
                path_id=path_id,
                start_ts=start_ts,
                end_ts=end_ts,
                duration_ms=duration_ms,
                context_bytes_loaded=context_bytes_loaded,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                retry_count=retry_count,
                compression_ratio=compression_ratio,
                details=details,
            )
        )
    except Exception as exc:
        if logger is not None:
            logger.debug("Failed to emit ask telemetry: %s", exc)


def upsert_ask_session(
    workspace_root: Path,
    agent_id: str,
    work_item_id: str,
    artifact_fingerprint: str,
    *,
    logger: Any | None = None,
) -> None:
    """Upsert SessionState for ask invocation. Best-effort."""
    try:
        import configparser

        profile_path = workspace_root / ".sdd" / "profile"
        workspace_id = "unknown"
        schema_version = ""
        if profile_path.exists():
            try:
                parser = configparser.ConfigParser()
                parser.read(profile_path)
                workspace_id = parser.get("sdd", "workspace_id", fallback="unknown")
            except Exception as exc:
                if logger is not None:
                    logger.debug("Failed to read config: %s", exc)

        runtime_dir = workspace_root / ".sdd" / "runtime"
        session = SessionState(
            workspace_id=workspace_id,
            agent_id=agent_id,
            work_item_id=work_item_id,
            artifact_fingerprint=artifact_fingerprint,
            schema_version=schema_version,
            policy_set_version=schema_version,
        )
        SessionManager(state_dir=runtime_dir).upsert(session)
    except Exception as exc:
        if logger is not None:
            logger.debug("Failed to upsert ask session: %s", exc)
