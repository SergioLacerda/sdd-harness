"""sdd ask — runtime token capture, telemetry sync, and command implementation."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from sdd_cli.commands._ask_backend._pipeline_runtime_support import (
    build_runtime_details,
    emit_ask_response,
    normalize_ask_inputs,
)
from sdd_cli.commands._ask_backend._pipeline_runtime_support import (
    check_budget_zone_and_compress as _support_check_budget_zone_and_compress,
)
from sdd_cli.services.ask_response import (
    emit_ask_json_response as _emit_ask_json_response,
)
from sdd_cli.services.ask_response import (
    emit_ask_text_response as _emit_ask_text_response,
)
from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext

from ._helpers import (
    _hash_query,
    _json_mode,
    _normalize_typer_value,
    _now,
    _prefer_full_summary,
    _render_context_output,
    _resolve_ask_degraded_reason,
    _resolve_ask_drift_type,
)
from ._pipeline_session import _load_ask_snapshot, _start_ask_session
from ._telemetry import (
    _build_and_output_dossier,
    _capture_effective_tokens_with_source,
    _handle_dossier_error,
    _resolve_dossier_budget,
)

logger = logging.getLogger(__name__)


def _check_budget_zone_and_compress(
    query: str,
    estimated_context_bytes: int,
    mandates_count: int,
    *,
    prefer_full_summary_fn: Any = _prefer_full_summary,
    logger: logging.Logger = logger,
) -> tuple[int, float | None]:
    return _support_check_budget_zone_and_compress(
        query,
        estimated_context_bytes,
        mandates_count,
        prefer_full_summary_fn=prefer_full_summary_fn,
        logger=logger,
    )


def _resolve_runtime_token_metrics(
    inputs: _AskInputs, output_text: str
) -> tuple[int | None, int | None, str]:
    from sdd_cli.commands import _ask_backend as _backend

    tokens_in, tokens_out, token_source = _capture_effective_tokens_with_source(
        inputs.tokens_input, inputs.tokens_output
    )
    if tokens_in is None or tokens_out is None:
        est_in, est_out, est_source = _backend._resolve_tokens(
            inputs.query, output_text
        )
        if tokens_in is None:
            tokens_in = est_in
        if tokens_out is None:
            tokens_out = est_out
        if token_source in {"", "unknown"}:
            token_source = est_source
    return tokens_in, tokens_out, token_source


def _sync_ask_runtime(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
) -> tuple[str, str]:
    from sdd_cli.commands import _ask_backend as _backend

    context_source = ask_snapshot["context_source"]
    fingerprint = ask_snapshot["fingerprint"]
    mandates_count = ask_snapshot["mandates_count"]
    authenticated = ask_snapshot["authenticated"]
    degraded = ask_snapshot["degraded"]
    degrade_reason = ask_snapshot["degrade_reason"]
    trust_source = ask_snapshot["trust_source"]
    drift_detected = ask_snapshot["drift_detected"]
    learning_signals = ask_snapshot["learning_signals"]
    end_ts = _now()
    duration_ms = int((time.monotonic() - session.start_mono) * 1000)
    output_text = _render_context_output(
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )
    tokens_in, tokens_out, token_source = _resolve_runtime_token_metrics(
        inputs, output_text
    )
    path_id = os.environ.get("SDD_PATH_ID") or (
        "PATH_B" if session.organize_used else "PATH_A"
    )
    drift_type = _resolve_ask_drift_type(
        drift_detected=drift_detected, authenticated=authenticated
    )
    effective_degraded_reason = _resolve_ask_degraded_reason(
        degraded=degraded, degrade_reason=degrade_reason, authenticated=authenticated
    )
    _backend._emit_ask_telemetry(
        "governance.ask",
        command="ask",
        workspace_root=session.workspace_root,
        trace_id=session.trace_id,
        agent_id=session.agent_id,
        fingerprint=fingerprint,
        context_source=context_source,
        mandates_count=mandates_count,
        profile=session.profile,
        state=session.state,
        drift_detected=drift_detected,
        query_hash=_hash_query(inputs.query),
        path_id=path_id,
        start_ts=session.start_ts,
        end_ts=end_ts,
        duration_ms=duration_ms,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        extra_details=build_runtime_details(
            fingerprint=fingerprint,
            degraded=degraded,
            degraded_reason=effective_degraded_reason,
            drift_type=drift_type,
            trust_source=trust_source,
            authenticated=authenticated,
            session=session,
            token_source=token_source,
            learning_signals=learning_signals,
            inputs=inputs,
        ),
    )
    _backend._write_runtime_cache(
        session.workspace_root,
        {
            "ts": _now(),
            "trace_id": session.trace_id,
            "context_source": context_source,
            "compiled_fingerprint_used": fingerprint,
            "mandates_loaded": mandates_count,
            "agent_id": session.agent_id,
            "degraded": degraded,
            "degraded_reason": effective_degraded_reason,
            "trust_source": trust_source,
        },
    )
    _backend._upsert_ask_session(
        session.workspace_root, session.agent_id, "ask", fingerprint
    )
    return output_text, _backend._governance_footer_for_state(
        state=session.state,
        profile=session.profile,
        drift_detected=drift_detected,
    )


def _ask_cmd_impl(
    *,
    query: str,
    dossier: bool,
    skill: str | None,
    budget: int | None,
    full: bool,
    log_path: str | None,
    log_format: str,
    tokens_input: int | None,
    tokens_output: int | None,
) -> None:
    inputs = normalize_ask_inputs(
        query=query,
        dossier=dossier,
        skill=skill,
        budget=budget,
        full=full,
        log_path=log_path,
        log_format=log_format,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        normalize_value_fn=_normalize_typer_value,
    )
    from sdd_cli.commands import _ask_backend as _backend

    session = _start_ask_session(inputs.query)
    ask_snapshot = _load_ask_snapshot(inputs, session)
    output_text, governance_footer = _sync_ask_runtime(inputs, session, ask_snapshot)
    emit_ask_response(
        inputs=inputs,
        session=session,
        ask_snapshot=ask_snapshot,
        output_text=output_text,
        governance_footer=governance_footer,
        json_mode_fn=_json_mode,
        emit_json_response_fn=_emit_ask_json_response,
        emit_text_response_fn=_emit_ask_text_response,
        resolve_dossier_budget_fn=_resolve_dossier_budget,
        load_dossier_artifact_fn=_backend._load_dossier_artifact,
        build_dossier_lines_fn=_backend._build_dossier_lines,
        handle_dossier_error_fn=_handle_dossier_error,
        prefer_full_summary_fn=_prefer_full_summary,
        build_and_output_dossier_fn=_build_and_output_dossier,
    )
