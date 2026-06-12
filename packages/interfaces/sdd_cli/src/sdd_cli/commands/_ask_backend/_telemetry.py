"""sdd_runtime telemetry, session, and dossier integration for ``sdd ask``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer
from sdd_runtime import OtelBridge as OtelBridge
from sdd_runtime import TelemetrySink as TelemetrySink
from sdd_runtime.otel import OtlpHttpExporter as OtlpHttpExporter

from sdd_cli.services.ask_dossier import (
    build_and_output_dossier as _build_and_output_dossier_impl,
)
from sdd_cli.services.ask_dossier import (
    build_dossier_lines as _build_dossier_lines_impl,
)
from sdd_cli.services.ask_dossier import (
    handle_dossier_error as _handle_dossier_error_impl,
)
from sdd_cli.services.ask_dossier import (
    load_dossier_artifact as _load_dossier_artifact_impl,
)
from sdd_cli.services.ask_dossier import (
    resolve_dossier_budget as _resolve_dossier_budget_impl,
)
from sdd_cli.services.ask_telemetry import (
    emit_ask_telemetry as _emit_ask_telemetry_impl,
)
from sdd_cli.services.ask_telemetry import (
    resolve_tokens as _resolve_tokens_impl,
)
from sdd_cli.services.ask_telemetry import (
    upsert_ask_session as _upsert_ask_session_impl,
)
from sdd_cli.utils.sdd_authority import compiled_active_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# sdd_runtime telemetry integration
# ---------------------------------------------------------------------------


def _resolve_tokens(query: str, output_text: str) -> tuple[int | None, int | None, str]:
    return _resolve_tokens_impl(query, output_text)


def _emit_ask_telemetry(
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
) -> None:
    from sdd_cli.commands import _ask_backend as _backend

    _emit_ask_telemetry_impl(
        event_name,
        command=command,
        workspace_root=workspace_root,
        trace_id=trace_id,
        agent_id=agent_id,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        profile=profile,
        state=state,
        drift_detected=drift_detected,
        query_hash=query_hash,
        path_id=path_id,
        start_ts=start_ts,
        end_ts=end_ts,
        duration_ms=duration_ms,
        context_bytes_loaded=context_bytes_loaded,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        retry_count=retry_count,
        compression_ratio=compression_ratio,
        extra_details=extra_details,
        logger=logger,
        telemetry_sink_cls=_backend.TelemetrySink,
        otel_bridge_cls=_backend.OtelBridge,
        otlp_exporter_cls=_backend.OtlpHttpExporter,
    )


# ---------------------------------------------------------------------------
# sdd_runtime session integration
# ---------------------------------------------------------------------------


def _upsert_ask_session(
    workspace_root: Path,
    agent_id: str,
    work_item_id: str,
    artifact_fingerprint: str,
) -> None:
    _upsert_ask_session_impl(
        workspace_root=workspace_root,
        agent_id=agent_id,
        work_item_id=work_item_id,
        artifact_fingerprint=artifact_fingerprint,
        logger=logger,
    )


# ---------------------------------------------------------------------------
# Dossier builder (C1)
# ---------------------------------------------------------------------------


def _handle_dossier_error(exc: Exception) -> None:
    _handle_dossier_error_impl(
        exc,
        logger=logger,
        typer_module=typer,
    )


def _build_and_output_dossier(
    query: str,
    skill: str | None,
    budget: int | None,
    mandates_count: int,
    workspace_root: Path | None = None,
) -> None:
    from sdd_cli.commands import _ask_backend as _backend

    _build_and_output_dossier_impl(
        query=query,
        skill=skill,
        budget=budget,
        mandates_count=mandates_count,
        workspace_root=workspace_root,
        resolve_workspace_root_fn=_backend._resolve_workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
        logger=logger,
        typer_module=typer,
    )


def _resolve_dossier_budget(budget: int | None) -> int:
    return _resolve_dossier_budget_impl(budget)


def _load_dossier_artifact(workspace_root: Path) -> Any | None:
    artifact = _load_dossier_artifact_impl(
        workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
    )
    if artifact is None:
        compiled_path = compiled_active_dir(workspace_root) / "governance-core.json"
        logger.debug("Could not load artifact from %s", compiled_path)
    return artifact


def _build_dossier_lines(
    query: str,
    skill: str | None,
    budget: int,
    mandates_count: int,
    budget_utilization_pct: float,
    context_result: Any,
) -> list[str]:
    return _build_dossier_lines_impl(
        query=query,
        skill=skill,
        budget=budget,
        mandates_count=mandates_count,
        budget_utilization_pct=budget_utilization_pct,
        context_result=context_result,
    )


# ---------------------------------------------------------------------------
# Token capture
# ---------------------------------------------------------------------------


def _capture_effective_tokens(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None]:
    """Capture token counts from CLI flags or environment variables.

    Backward-compatible public helper that returns only token counts.
    """
    effective_tokens_input, effective_tokens_output, _ = (
        _capture_effective_tokens_with_source(tokens_input, tokens_output)
    )
    return effective_tokens_input, effective_tokens_output


def _capture_effective_tokens_with_source(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None, str]:
    """Capture token counts and source from CLI flags or environment variables."""
    from sdd_runtime.llm import SimulatedTokenCapture

    effective_tokens_input = tokens_input
    effective_tokens_output = tokens_output
    token_source = (
        "cli" if tokens_input is not None or tokens_output is not None else ""
    )
    if effective_tokens_input is None or effective_tokens_output is None:
        captured = SimulatedTokenCapture().capture_from_env()
        if captured:
            if effective_tokens_input is None:
                effective_tokens_input = captured.tokens_input
            if effective_tokens_output is None:
                effective_tokens_output = captured.tokens_output
            token_source = token_source or "env"
    return effective_tokens_input, effective_tokens_output, token_source or "unknown"
