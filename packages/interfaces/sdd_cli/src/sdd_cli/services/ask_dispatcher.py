"""ask_dispatcher — orchestrates the sdd ask pipeline.

Entry point: run_ask(). Calls ask_context → ask_filter → ask_renderer in order.
All I/O (stdout/stderr) is performed here, keeping renderer functions pure.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

from sdd_cli.services.ask_context import (
    AskContext,
    load_ask_context,
    resolve_workspace_root,
    write_runtime_cache,
)
from sdd_cli.services.ask_filter import collect_learning_signals
from sdd_cli.services.ask_renderer import (
    build_ask_json_payload,
    render_ask_text_output,
    render_context_header,
    render_governance_footer,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class AskArgs:
    """Canonical input arguments for the sdd ask pipeline."""

    query: str
    dossier: bool = False
    skill: str | None = None
    budget: int | None = None
    full: bool = False
    log_path: str | None = None
    log_format: str = "jsonl"
    tokens_input: int | None = None
    tokens_output: int | None = None
    output_json: bool = False


def _resolve_drift_type(*, drift_detected: bool, authenticated: bool) -> str:
    if not drift_detected:
        return "none"
    return "auth_drift" if not authenticated else "fingerprint_drift"


def _resolve_degraded_reason(
    *, degraded: bool, degrade_reason: str, authenticated: bool
) -> str:
    if degrade_reason.strip():
        return degrade_reason.strip()
    if degraded and not authenticated:
        return "artifact_unverified"
    if degraded:
        return "degraded_unspecified"
    return ""


def _capture_tokens(
    tokens_input: int | None, tokens_output: int | None
) -> tuple[int | None, int | None, str]:
    from sdd_runtime.llm import SimulatedTokenCapture

    source = "cli" if tokens_input is not None or tokens_output is not None else ""
    if tokens_input is None or tokens_output is None:
        captured = SimulatedTokenCapture().capture_from_env()
        if captured:
            if tokens_input is None:
                tokens_input = captured.tokens_input
            if tokens_output is None:
                tokens_output = captured.tokens_output
            source = source or "env"
    return tokens_input, tokens_output, source or "unknown"


def _emit_telemetry(
    *,
    ctx: AskContext,
    args: AskArgs,
    trace_id: str,
    agent_id: str,
    start_ts: str,
    drift_type: str,
    effective_degraded_reason: str,
    organize_used: bool,
    organize_reason: str,
    organize_artifact_path: str,
    organize_chunks: int,
    organize_retrieval: str,
    token_source: str,
    tokens_in: int | None,
    tokens_out: int | None,
    duration_ms: int,
    learning_signals: dict[str, int],
) -> None:
    from sdd_runtime import OtelBridge, TelemetrySink
    from sdd_runtime.otel import OtlpHttpExporter

    from sdd_cli.services.ask_telemetry import emit_ask_telemetry

    emit_ask_telemetry(
        "governance.ask",
        command="ask",
        workspace_root=ctx.workspace_root,
        trace_id=trace_id,
        agent_id=agent_id,
        fingerprint=ctx.fingerprint,
        context_source=ctx.context_source,
        mandates_count=ctx.mandates_count,
        profile=ctx.profile,
        state=ctx.ahp_state,
        drift_detected=ctx.drift_detected,
        query_hash=_hash_query(args.query),
        path_id=os.environ.get("SDD_PATH_ID")
        or ("PATH_B" if organize_used else "PATH_A"),
        start_ts=start_ts,
        end_ts=_now(),
        duration_ms=duration_ms,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        extra_details={
            "compiled_fingerprint_used": ctx.fingerprint,
            "degraded": ctx.degraded,
            "degraded_reason": effective_degraded_reason,
            "drift_type": drift_type,
            "trust_source": ctx.trust_source,
            "authenticated": ctx.authenticated,
            "intake_route": "heavy" if organize_used else "light",
            "intake_route_reason": organize_reason,
            "intake_artifact": organize_artifact_path,
            "intake_chunks": organize_chunks,
            "intake_retrieval": organize_retrieval,
            "token_source": token_source,
            "learning_signal_count": sum(
                v
                for k, v in learning_signals.items()
                if k not in {"observed_events", "window_days"}
            ),
            "full_mode": args.full,
            "log_format": args.log_format,
            "log_path": args.log_path or "default",
        },
        logger=logger,
        telemetry_sink_cls=TelemetrySink,
        otel_bridge_cls=OtelBridge,
        otlp_exporter_cls=OtlpHttpExporter,
    )


def _hash_query(query: str) -> str:
    import hashlib

    return hashlib.sha256(query.encode()).hexdigest()[:8]


def _build_dossier_lines_for_json(args: AskArgs, ctx: AskContext) -> list[str]:
    if not args.dossier:
        return []
    try:
        from sdd_runtime.context import ContextLoader, ContextRequest

        from sdd_cli.services.ask_dossier import (
            build_dossier_lines,
            load_dossier_artifact,
            resolve_dossier_budget,
        )

        prefer_full = os.environ.get(
            "SDD_ASK_PREFER_FULL_SUMMARY", ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        dossier_budget = resolve_dossier_budget(args.budget)
        artifact = load_dossier_artifact(
            ctx.workspace_root,
            compiled_active_dir_fn=_compiled_active_dir(),
        )
        context_result = ContextLoader().load_result(
            ContextRequest(
                query=args.query,
                artifact=artifact,
                max_items=ctx.mandates_count,
                budget_utilization_pct=50.0,
                prefer_full_summary=prefer_full,
            )
        )
        return build_dossier_lines(
            query=args.query,
            skill=args.skill,
            budget=dossier_budget,
            mandates_count=ctx.mandates_count,
            budget_utilization_pct=50.0,
            context_result=context_result,
        )
    except Exception as exc:
        logger.debug("Dossier build failed: %s", exc)
        return []


def _compiled_active_dir() -> Any:
    from sdd_cli.utils.sdd_authority import compiled_active_dir

    return compiled_active_dir


def _run_organize_if_needed(
    query: str, workspace_root: Path
) -> tuple[bool, str, str, int, str]:
    """Run sdd-organize if appropriate. Returns (used, reason, artifact_path, chunks, retrieval)."""
    from sdd_cli.services.ask_organize import run_sdd_organize, should_use_organize

    organize_used, organize_reason = should_use_organize(query)
    organize_artifact_path = ""
    organize_chunks = 0
    organize_retrieval = "indexed_only"
    if organize_used:
        try:
            artifact_data, organize_path = run_sdd_organize(
                workspace_root=workspace_root,
                query=query,
                source_text=query,
                route_reason=organize_reason,
            )
            organize_artifact_path = str(organize_path)
            organize_chunks = len(artifact_data.get("chunks", []))
            organize_retrieval = str(
                artifact_data.get("retrieval_policy", "indexed_only")
            )
        except Exception as exc:
            logger.debug("sdd-organize failed: %s", exc)
            organize_retrieval = "degraded"
    return (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
    )


def run_ask(args: AskArgs) -> None:
    """Execute the full sdd ask pipeline. Performs all I/O."""
    from sdd_cli.utils.output import emit_json

    start_mono = time.monotonic()
    start_ts = _now()

    workspace_root = resolve_workspace_root()

    (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
    ) = _run_organize_if_needed(args.query, workspace_root)

    ctx = load_ask_context(workspace_root)
    agent_id = os.environ.get("SDD_AGENT_ID", "unknown")
    trace_id = str(uuid.uuid4())

    if not args.output_json and ctx.ahp_state in ("NOT_INITIALIZED", "MISCONFIGURED"):
        typer.echo(
            f"SOFT [ask]: workspace {ctx.ahp_state}. Run 'sdd governance compile' before using ask.",
            err=True,
        )
    elif not args.output_json and ctx.ahp_state == "PARTIAL":
        typer.echo(
            "SOFT [ask]: workspace PARTIAL — compiled governance may be stale. "
            "Next: 'sdd governance compile'",
            err=True,
        )

    learning_signals = collect_learning_signals(workspace_root)
    effective_degraded_reason = _resolve_degraded_reason(
        degraded=ctx.degraded,
        degrade_reason=ctx.degrade_reason,
        authenticated=ctx.authenticated,
    )
    drift_type = _resolve_drift_type(
        drift_detected=ctx.drift_detected, authenticated=ctx.authenticated
    )

    output_text = render_context_header(
        ctx.fingerprint,
        ctx.mandates_count,
        degraded=ctx.degraded,
        degrade_reason=ctx.degrade_reason,
    )
    governance_footer = render_governance_footer(
        state=ctx.ahp_state,
        profile=ctx.profile,
        drift_detected=ctx.drift_detected,
    )

    tokens_in, tokens_out, token_source = _capture_tokens(
        args.tokens_input, args.tokens_output
    )
    if tokens_in is None or tokens_out is None:
        from sdd_cli.services.ask_telemetry import resolve_tokens

        est_in, est_out, est_source = resolve_tokens(args.query, output_text)
        if tokens_in is None:
            tokens_in = est_in
        if tokens_out is None:
            tokens_out = est_out
        if token_source in {"", "unknown"}:
            token_source = est_source

    duration_ms = int((time.monotonic() - start_mono) * 1000)

    _emit_telemetry(
        ctx=ctx,
        args=args,
        trace_id=trace_id,
        agent_id=agent_id,
        start_ts=start_ts,
        drift_type=drift_type,
        effective_degraded_reason=effective_degraded_reason,
        organize_used=organize_used,
        organize_reason=organize_reason,
        organize_artifact_path=organize_artifact_path,
        organize_chunks=organize_chunks,
        organize_retrieval=organize_retrieval,
        token_source=token_source,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms,
        learning_signals=learning_signals,
    )

    write_runtime_cache(
        workspace_root,
        {
            "ts": _now(),
            "trace_id": trace_id,
            "context_source": ctx.context_source,
            "compiled_fingerprint_used": ctx.fingerprint,
            "mandates_loaded": ctx.mandates_count,
            "agent_id": agent_id,
            "degraded": ctx.degraded,
            "degraded_reason": effective_degraded_reason,
            "trust_source": ctx.trust_source,
        },
    )

    from sdd_cli.services.ask_telemetry import upsert_ask_session

    upsert_ask_session(
        workspace_root=workspace_root,
        agent_id=agent_id,
        work_item_id="ask",
        artifact_fingerprint=ctx.fingerprint,
        logger=logger,
    )

    if args.output_json:
        dossier_lines = _build_dossier_lines_for_json(args, ctx)
        payload = build_ask_json_payload(
            profile=ctx.profile,
            query=args.query,
            context_source=ctx.context_source,
            fingerprint=ctx.fingerprint,
            mandates_count=ctx.mandates_count,
            trust_source=ctx.trust_source,
            degraded=ctx.degraded,
            degrade_reason=ctx.degrade_reason,
            drift_detected=ctx.drift_detected,
            governance_footer=governance_footer,
            organize_used=organize_used,
            organize_chunks=organize_chunks,
            organize_retrieval=organize_retrieval,
            organize_artifact_path=organize_artifact_path,
            ahp_state=ctx.ahp_state,
            learning_signals=learning_signals,
            full=args.full,
            start_ts=start_ts,
            dossier_lines=dossier_lines if dossier_lines else None,
        )
        emit_json(payload)
        return

    text_output = render_ask_text_output(
        output_text=output_text,
        organize_used=organize_used,
        organize_chunks=organize_chunks,
        organize_artifact_path=organize_artifact_path,
        query_len=len(args.query),
        governance_footer=governance_footer,
    )
    typer.echo(text_output)

    if args.dossier:
        from sdd_cli.services.ask_dossier import build_and_output_dossier
        from sdd_cli.utils.sdd_authority import compiled_active_dir

        build_and_output_dossier(
            query=args.query,
            skill=args.skill,
            budget=args.budget,
            mandates_count=ctx.mandates_count,
            workspace_root=workspace_root,
            resolve_workspace_root_fn=resolve_workspace_root,
            compiled_active_dir_fn=compiled_active_dir,
            logger=logger,
            typer_module=typer,
        )
